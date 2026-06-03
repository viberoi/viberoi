"""Long-poll SQS `backfill_jobs` and dispatch to `run_sync`.

Failure handling mirrors worker/app/consumer.py: bad envelope → ack
(unrecoverable); processing failure → DO NOT ack so SQS redelivers + DLQs
after `maxReceiveCount=3`.

Launched alongside uvicorn by `entrypoint.sh`.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import orjson

from integration.app.sync import SyncRequest, run_sync
from viberoi_shared.errors import NotFound
from viberoi_shared.logging import get_logger
from viberoi_shared.sqs import delete, receive

logger = get_logger(__name__)

QUEUE_NAME = "backfill_jobs"
_BATCH_SIZE = 5
_LONG_POLL_S = 20
_BACKOFF_S = 1.0

VALID_SYNC_TYPES = {"initial_90d", "delta", "manual"}


async def run() -> None:
    """Consumer main loop. Runs forever until cancelled."""
    logger.info("integration_consumer_starting", queue=QUEUE_NAME)
    try:
        while True:
            try:
                messages = await receive(
                    QUEUE_NAME, max_messages=_BATCH_SIZE, wait_seconds=_LONG_POLL_S
                )
            except Exception as e:
                logger.exception("sqs_receive_failed", error=str(e))
                await asyncio.sleep(_BACKOFF_S)
                continue

            for msg in messages:
                await _handle_message(msg)
    except asyncio.CancelledError:
        logger.info("integration_consumer_cancelled")
        raise


async def _handle_message(msg: dict[str, Any]) -> None:
    message_id = msg.get("MessageId", "unknown")
    try:
        body = orjson.loads(msg["Body"])
        request = _parse_request(body)
    except Exception as e:
        logger.exception(
            "backfill_envelope_invalid_acked",
            message_id=message_id,
            error=str(e),
        )
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
        return

    try:
        await run_sync(request)
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
    except NotFound:
        # Integration was revoked between enqueue and process; nothing to do.
        logger.info(
            "backfill_integration_missing_acked",
            message_id=message_id,
            provider=request.provider,
            org_id=str(request.org_id),
        )
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
    except Exception as e:
        logger.exception(
            "backfill_failed_will_retry",
            message_id=message_id,
            provider=request.provider,
            org_id=str(request.org_id),
            error=str(e),
        )


def _parse_request(body: dict[str, Any]) -> SyncRequest:
    """Strict envelope parse — surface bad inputs to DLQ via the caller's try."""
    org_id = UUID(body["org_id"])
    provider = str(body["provider"])
    sync_type = str(body.get("sync_type", "delta"))
    if sync_type not in VALID_SYNC_TYPES:
        raise ValueError(f"invalid sync_type: {sync_type}")
    return SyncRequest(org_id=org_id, provider=provider, sync_type=sync_type)
