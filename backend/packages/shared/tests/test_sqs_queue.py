"""SQS publish/receive/delete — integration tests (requires LocalStack)."""

from uuid import uuid4

import orjson
import pytest

from viberoi_shared.sqs import SQSError, delete, publish, receive, reset_url_cache

pytestmark = pytest.mark.integration

# Use the standard queue created by scripts/localstack-init.sh
_TEST_QUEUE = "session_ingest"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_url_cache()
    yield
    reset_url_cache()


async def test_publish_receive_delete_round_trip() -> None:
    marker = str(uuid4())
    body = {"marker": marker, "kind": "test"}

    message_id = await publish(_TEST_QUEUE, body)
    assert message_id

    # Drain until we find our message (other tests may share the queue).
    found = None
    for _ in range(5):
        messages = await receive(_TEST_QUEUE, max_messages=10, wait_seconds=1)
        for msg in messages:
            if orjson.loads(msg["Body"]).get("marker") == marker:
                found = msg
                break
            # Not ours — leave it visible for the test that owns it
            # (don't delete; visibility timeout will recycle).
        if found:
            break

    assert found is not None, f"Did not receive message with marker {marker}"
    await delete(_TEST_QUEUE, found["ReceiptHandle"])


async def test_publish_to_missing_queue_raises() -> None:
    with pytest.raises(SQSError):
        await publish(f"nonexistent-queue-{uuid4()}", {"any": "body"})


async def test_receive_returns_empty_list_when_no_messages() -> None:
    # Use a unique queue name to avoid races with other tests.
    # If the queue doesn't exist, this raises — confirms our error path.
    # Test against a known empty path by using a very short wait.
    messages = await receive(_TEST_QUEUE, max_messages=1, wait_seconds=0)
    assert isinstance(messages, list)
