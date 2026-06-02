"""Long-poll SQS `session_ingest` and dispatch each message to the processor.

Failure handling: an exception during processing intentionally does NOT
ack the SQS message. SQS makes it visible again after VisibilityTimeout
(30s) and eventually moves to the DLQ after `maxReceiveCount=3` attempts.
This avoids losing data on transient errors.
"""

import asyncio

import orjson

from viberoi_shared.logging import get_logger
from viberoi_shared.sqs import delete, receive

from worker.app.processor import process_s3_event
from worker.schema.events import S3EventEnvelope

logger = get_logger(__name__)

QUEUE_NAME = "session_ingest"
_BATCH_SIZE = 10
_LONG_POLL_S = 20
_BACKOFF_S = 1.0


async def run() -> None:
    """Consumer main loop. Runs forever until cancelled."""
    logger.info("worker_consumer_starting", queue=QUEUE_NAME)
    try:
        while True:
            try:
                messages = await receive(
                    QUEUE_NAME, max_messages=_BATCH_SIZE, wait_seconds=_LONG_POLL_S
                )
            except Exception as e:  # noqa: BLE001
                logger.exception("sqs_receive_failed", error=str(e))
                await asyncio.sleep(_BACKOFF_S)
                continue

            for msg in messages:
                await _handle_message(msg)
    except asyncio.CancelledError:
        logger.info("worker_consumer_cancelled")
        raise


async def _handle_message(msg: dict) -> None:
    message_id = msg.get("MessageId", "unknown")
    try:
        payload = orjson.loads(msg["Body"])
        envelope = S3EventEnvelope.model_validate(payload)
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "sqs_envelope_invalid_will_dlq",
            message_id=message_id,
            error=str(e),
        )
        # Bad envelope is unrecoverable — ack so it doesn't loop forever.
        # The retry-via-DLQ pattern is for transient/processing failures.
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
        return

    try:
        for record in envelope.records:
            await process_s3_event(record)
        await delete(QUEUE_NAME, msg["ReceiptHandle"])
    except Exception as e:  # noqa: BLE001
        # Don't ack — SQS will redeliver. DLQ kicks in after maxReceiveCount.
        logger.exception(
            "process_failed_will_retry",
            message_id=message_id,
            error=str(e),
        )
