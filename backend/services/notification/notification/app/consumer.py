"""Long-poll SQS `notification_jobs` and dispatch to channel handlers.

Failure handling — mirrors worker/app/consumer.py:
  - Bad envelope / unknown template / circuit-open / channel missing
    → ack (unrecoverable, no point retrying).
  - Permanent delivery failure (4xx that isn't 429) → ack + disable
    channel. The OrgAdmin re-enables once they've fixed the URL.
  - Transient delivery failure → DON'T ack. SQS redelivers; the DLQ
    catches after `maxReceiveCount=3`.
"""

from __future__ import annotations

import asyncio
from typing import Any

import orjson

from notification.app import circuit_breaker
from notification.app.handlers.slack import deliver as slack_deliver
from notification.app.templates import UnknownTemplateError, render
from viberoi_shared.db import org_scoped_session, superuser_session
from viberoi_shared.logging import get_logger
from viberoi_shared.notifications import (
    NotificationEnvelope,
    disable_channel,
    get_channel_for_org,
)
from viberoi_shared.sqs import delete, receive

logger = get_logger(__name__)

QUEUE_NAME = "notification_jobs"
_BATCH_SIZE = 5
_LONG_POLL_S = 20
_BACKOFF_S = 1.0


async def run() -> None:
    """Consumer main loop. Runs forever until cancelled."""
    logger.info("notification_consumer_starting", queue=QUEUE_NAME)
    try:
        while True:
            try:
                messages = await receive(
                    QUEUE_NAME, max_messages=_BATCH_SIZE, wait_seconds=_LONG_POLL_S
                )
            except Exception as e:  # noqa: BLE001
                logger.exception("sqs_receive_failed", error_type=type(e).__name__)
                await asyncio.sleep(_BACKOFF_S)
                continue

            for msg in messages:
                await _handle_message(msg)
    except asyncio.CancelledError:
        logger.info("notification_consumer_cancelled")
        raise


async def _handle_message(msg: dict[str, Any]) -> None:
    message_id = msg.get("MessageId", "unknown")

    try:
        body = orjson.loads(msg["Body"])
        envelope = NotificationEnvelope.model_validate(body)
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "notification_envelope_invalid_acked",
            message_id=message_id,
            error_type=type(e).__name__,
        )
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
        return

    log_ctx = {
        "message_id": message_id,
        "org_id": str(envelope.org_id),
        "channel": envelope.channel,
        "template": envelope.template,
        "trace_id": str(envelope.trace_id),
    }

    # 1. Circuit breaker check
    if await circuit_breaker.is_open(envelope.org_id, envelope.channel):
        logger.warning("notification_circuit_open_acked", **log_ctx)
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
        return

    # 2. Render template (cheap, fails fast if name is unknown)
    try:
        rendered = render(envelope.template, envelope.payload)
    except UnknownTemplateError:
        logger.warning("notification_unknown_template_acked", **log_ctx)
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
        return

    # 3. Load decrypted channel config
    async with org_scoped_session(envelope.org_id) as db:
        config = await get_channel_for_org(
            db, org_id=envelope.org_id, channel=envelope.channel
        )

    if config is None or config.get("webhook_url") is None:
        # No channel configured for this (org, channel) — nothing to do.
        # Common case: the org never set up Slack, but a fan-out fired
        # for them anyway.
        logger.info("notification_no_channel_acked", **log_ctx)
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
        return

    # 4. Deliver
    if envelope.channel == "slack":
        result = await slack_deliver(
            webhook_url=config["webhook_url"], payload=rendered
        )
    else:
        # Unknown channel kind reaching the consumer — surface as
        # unknown-template-style ack; we shouldn't be enqueueing for
        # channel types we don't deliver.
        logger.warning(
            "notification_unknown_channel_acked", **log_ctx
        )
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
        return

    # 5. Act on the outcome
    if result.ok:
        await circuit_breaker.record_success(envelope.org_id, envelope.channel)
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
        logger.info(
            "notification_delivered",
            status_code=result.status_code,
            **log_ctx,
        )
        return

    if result.permanent:
        # 4xx (other than 429) — the URL is broken or revoked. Disable
        # the channel + ack; we don't want to redeliver a doomed
        # message until the DLQ catches it 3 receives later.
        async with superuser_session() as db:
            await disable_channel(
                db, org_id=envelope.org_id, channel=envelope.channel
            )
        logger.warning(
            "notification_permanent_failure_channel_disabled",
            status_code=result.status_code,
            **log_ctx,
        )
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
        return

    # Transient failure — DON'T ack; SQS redelivers, breaker may open.
    failures = await circuit_breaker.record_failure(
        envelope.org_id, envelope.channel
    )
    logger.warning(
        "notification_transient_failure_will_retry",
        status_code=result.status_code,
        failures=failures,
        **log_ctx,
    )
