"""SQS publish + consume helpers.

Standard queues from `scripts/localstack-init.sh` / Terraform:
  session_ingest, webhook_events, backfill_jobs, notification_jobs

Each has a DLQ with `maxReceiveCount=3` and `VisibilityTimeout=30`.
The Worker (and Notification consumer) follow the receive → process
→ delete pattern; on processing failure, do NOT delete — SQS will
re-deliver and eventually move to DLQ.

Queue URLs are resolved lazily and cached per process.
"""

from typing import Any

import orjson

from viberoi_shared.aws import sqs_client
from viberoi_shared.errors.types import VibeRoiError
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)


class SQSError(VibeRoiError):
    code = "sqs_error"
    safe_message = "SQS operation failed."


# queue_name → URL cache (LocalStack URLs differ from prod URLs).
_url_cache: dict[str, str] = {}


async def _queue_url(queue_name: str) -> str:
    if queue_name in _url_cache:
        return _url_cache[queue_name]
    async with sqs_client() as sqs:
        try:
            resp = await sqs.get_queue_url(QueueName=queue_name)
        except Exception as e:
            raise SQSError(f"Could not resolve queue URL for {queue_name}") from e
    url = resp["QueueUrl"]
    _url_cache[queue_name] = url
    return url


def reset_url_cache() -> None:
    """For tests."""
    _url_cache.clear()


async def publish(
    queue_name: str,
    body: dict[str, Any],
    *,
    deduplication_id: str | None = None,
) -> str:
    """Publish a JSON message. Returns the SQS MessageId.

    `deduplication_id` is only honored on FIFO queues. For standard
    queues it's silently ignored by SQS.
    """
    queue_url = await _queue_url(queue_name)
    payload = orjson.dumps(body).decode("utf-8")

    kwargs: dict[str, Any] = {"QueueUrl": queue_url, "MessageBody": payload}
    if deduplication_id:
        kwargs["MessageDeduplicationId"] = deduplication_id

    async with sqs_client() as sqs:
        try:
            resp = await sqs.send_message(**kwargs)
        except Exception as e:
            raise SQSError(f"Failed to publish to {queue_name}") from e

    logger.info("sqs_published", queue=queue_name, message_id=resp["MessageId"])
    return resp["MessageId"]


async def receive(
    queue_name: str,
    *,
    max_messages: int = 10,
    wait_seconds: int = 20,
) -> list[dict[str, Any]]:
    """Long-poll a queue. Returns raw message dicts.

    Each message has `MessageId`, `Body`, `ReceiptHandle`, plus optional
    attributes. The caller must `delete()` the message after successful
    processing — otherwise it will become visible again after the
    queue's `VisibilityTimeout` and eventually move to the DLQ.

    `wait_seconds` enables long polling; up to 20s per SQS.
    """
    queue_url = await _queue_url(queue_name)
    async with sqs_client() as sqs:
        try:
            resp = await sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_seconds,
            )
        except Exception as e:
            raise SQSError(f"Failed to receive from {queue_name}") from e
    return resp.get("Messages", [])


async def delete(queue_name: str, receipt_handle: str) -> None:
    """Acknowledge a message; removes it from the queue."""
    queue_url = await _queue_url(queue_name)
    async with sqs_client() as sqs:
        try:
            await sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        except Exception as e:
            raise SQSError(f"Failed to delete message from {queue_name}") from e
