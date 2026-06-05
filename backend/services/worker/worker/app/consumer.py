"""Long-poll SQS queues + dispatch each message to its processor.

Two queues run in parallel asyncio tasks:

- `session_ingest` — S3 event envelopes from the raw-landing bucket.
  Each message points at a gzipped Session JSON to fetch + process.
- `webhook_events` — verified provider webhook envelopes from the
  receiver Lambda. Each message is a parsed envelope ready to dispatch
  to provider event handlers.

Failure handling per message: an exception during processing does NOT
ack. SQS makes the message visible again after VisibilityTimeout
(30s) and eventually moves it to the DLQ after `maxReceiveCount=3`
attempts. This avoids losing data on transient errors.
"""

from __future__ import annotations

import asyncio

import orjson

from viberoi_shared.logging import get_logger
from viberoi_shared.sqs import delete, receive

from worker.app.processor import process_s3_event
from worker.app.webhook_processor import process_webhook
from worker.schema.events import S3EventEnvelope
from worker.schema.webhook_events import WebhookEnvelope

logger = get_logger(__name__)

SESSION_QUEUE = "session_ingest"
WEBHOOK_QUEUE = "webhook_events"
_BATCH_SIZE = 10
_LONG_POLL_S = 20
_BACKOFF_S = 1.0


async def run() -> None:
    """Run both consumers concurrently. One stalls → the other keeps going.

    Cancellation of either propagates to the gather, so SIGTERM cleanly
    stops both consumers.
    """
    logger.info(
        "worker_consumers_starting",
        queues=[SESSION_QUEUE, WEBHOOK_QUEUE],
    )
    await asyncio.gather(
        _consume_session_ingest(),
        _consume_webhook_events(),
    )


# ── Session ingest consumer (S3 events) ────────────────────────────────────


async def _consume_session_ingest() -> None:
    try:
        while True:
            try:
                messages = await receive(
                    SESSION_QUEUE,
                    max_messages=_BATCH_SIZE,
                    wait_seconds=_LONG_POLL_S,
                )
            except Exception as e:  # noqa: BLE001
                logger.exception("sqs_receive_failed", queue=SESSION_QUEUE, error=str(e))
                await asyncio.sleep(_BACKOFF_S)
                continue
            for msg in messages:
                await _handle_session_message(msg)
    except asyncio.CancelledError:
        logger.info("session_consumer_cancelled")
        raise


async def _handle_session_message(msg: dict) -> None:
    message_id = msg.get("MessageId", "unknown")
    try:
        payload = orjson.loads(msg["Body"])
        envelope = S3EventEnvelope.model_validate(payload)
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "session_envelope_invalid_will_drop",
            message_id=message_id,
            error=str(e),
        )
        await delete(SESSION_QUEUE, msg["ReceiptHandle"])
        return

    try:
        for record in envelope.records:
            await process_s3_event(record)
        await delete(SESSION_QUEUE, msg["ReceiptHandle"])
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "session_process_failed_will_retry",
            message_id=message_id,
            error=str(e),
        )


# ── Webhook events consumer ────────────────────────────────────────────────


async def _consume_webhook_events() -> None:
    try:
        while True:
            try:
                messages = await receive(
                    WEBHOOK_QUEUE,
                    max_messages=_BATCH_SIZE,
                    wait_seconds=_LONG_POLL_S,
                )
            except Exception as e:  # noqa: BLE001
                logger.exception("sqs_receive_failed", queue=WEBHOOK_QUEUE, error=str(e))
                await asyncio.sleep(_BACKOFF_S)
                continue
            for msg in messages:
                await _handle_webhook_message(msg)
    except asyncio.CancelledError:
        logger.info("webhook_consumer_cancelled")
        raise


async def _handle_webhook_message(msg: dict) -> None:
    message_id = msg.get("MessageId", "unknown")
    try:
        payload = orjson.loads(msg["Body"])
        envelope = WebhookEnvelope.model_validate(payload)
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "webhook_envelope_invalid_will_drop",
            message_id=message_id,
            error=str(e),
        )
        await delete(WEBHOOK_QUEUE, msg["ReceiptHandle"])
        return

    try:
        await process_webhook(envelope)
        await delete(WEBHOOK_QUEUE, msg["ReceiptHandle"])
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "webhook_process_failed_will_retry",
            message_id=message_id,
            error=str(e),
        )
