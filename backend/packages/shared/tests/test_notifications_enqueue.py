"""Tests for `viberoi_shared.notifications.enqueue`.

SQS mocked — no LocalStack required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from viberoi_shared.notifications import NotificationEnvelope, enqueue
from viberoi_shared.notifications import publisher as enqueue_module


@pytest.fixture
def _stub_sqs(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value="msg-1")
    monkeypatch.setattr(enqueue_module, "sqs_publish", mock)
    return mock


async def test_enqueue_publishes_envelope(_stub_sqs: AsyncMock) -> None:
    org = uuid4()
    trace_id = await enqueue(
        org_id=org,
        channel="slack",
        template="integration_revoked",
        payload={"provider": "github"},
    )
    assert isinstance(trace_id, UUID)

    queue, body = _stub_sqs.call_args.args
    assert queue == "notification_jobs"
    assert body["org_id"] == str(org)
    assert body["channel"] == "slack"
    assert body["template"] == "integration_revoked"
    assert body["payload"] == {"provider": "github"}
    assert body["trace_id"] == str(trace_id)


async def test_enqueue_namespaces_dedup_id_by_org(_stub_sqs: AsyncMock) -> None:
    """Cross-tenant dedup-collision defense: two orgs with the same
    `dedup_key` must produce different SQS-level dedup ids."""
    org_a = uuid4()
    org_b = uuid4()
    await enqueue(
        org_id=org_a, channel="slack", template="t", dedup_key="X"
    )
    a_id = _stub_sqs.call_args.kwargs["deduplication_id"]
    await enqueue(
        org_id=org_b, channel="slack", template="t", dedup_key="X"
    )
    b_id = _stub_sqs.call_args.kwargs["deduplication_id"]
    assert a_id != b_id
    assert str(org_a) in a_id
    assert str(org_b) in b_id


async def test_enqueue_dedup_id_omitted_when_no_key(
    _stub_sqs: AsyncMock,
) -> None:
    await enqueue(org_id=uuid4(), channel="slack", template="t")
    assert _stub_sqs.call_args.kwargs["deduplication_id"] is None


async def test_envelope_round_trip() -> None:
    """Wire envelope is a strict Pydantic model — extra fields rejected."""
    payload = NotificationEnvelope(
        org_id=uuid4(),
        channel="slack",
        template="t",
        trace_id=uuid4(),
    )
    raw = payload.model_dump(mode="json")
    again = NotificationEnvelope.model_validate(raw)
    assert again == payload


async def test_envelope_rejects_extra_field() -> None:
    with pytest.raises(Exception):  # ValidationError
        NotificationEnvelope.model_validate(
            {
                "org_id": str(uuid4()),
                "channel": "slack",
                "template": "t",
                "trace_id": str(uuid4()),
                "unexpected_field": "bad",
            }
        )
