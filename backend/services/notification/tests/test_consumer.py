"""Notification consumer ack/no-ack semantics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import orjson
import pytest

from notification.app import consumer
from notification.app.handlers.slack import DeliveryResult


def _msg(body: dict) -> dict:
    return {
        "MessageId": "m1",
        "ReceiptHandle": "rh1",
        "Body": orjson.dumps(body).decode(),
    }


def _envelope(*, channel: str = "slack", template: str = "integration_revoked") -> dict:
    return {
        "org_id": str(uuid4()),
        "channel": channel,
        "template": template,
        "payload": {"provider": "github"},
        "trace_id": str(uuid4()),
        "dedup_key": None,
    }


@pytest.fixture
def patch_io(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(consumer, "delete", AsyncMock())
    monkeypatch.setattr(consumer.circuit_breaker, "is_open", AsyncMock(return_value=False))
    monkeypatch.setattr(consumer.circuit_breaker, "record_failure", AsyncMock(return_value=1))
    monkeypatch.setattr(consumer.circuit_breaker, "record_success", AsyncMock())

    # DB session ctx
    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(consumer, "org_scoped_session", lambda _: _Ctx())
    monkeypatch.setattr(consumer, "superuser_session", lambda: _Ctx())
    # Default: a configured Slack channel
    monkeypatch.setattr(
        consumer,
        "get_channel_for_org",
        AsyncMock(return_value={"webhook_url": "https://hooks.slack.com/xx", "config": {}}),
    )
    monkeypatch.setattr(consumer, "disable_channel", AsyncMock(return_value=True))
    monkeypatch.setattr(consumer, "slack_deliver", AsyncMock(return_value=DeliveryResult(ok=True, permanent=False, status_code=200)))
    return consumer


async def test_happy_path_acks(patch_io) -> None:
    await patch_io._handle_message(_msg(_envelope()))
    patch_io.delete.assert_awaited_once()
    patch_io.circuit_breaker.record_success.assert_awaited_once()


async def test_bad_envelope_acks(patch_io) -> None:
    await patch_io._handle_message(
        {"MessageId": "m", "ReceiptHandle": "rh", "Body": "not-json{"}
    )
    patch_io.delete.assert_awaited_once()


async def test_circuit_open_acks_without_delivery(patch_io) -> None:
    patch_io.circuit_breaker.is_open.return_value = True
    await patch_io._handle_message(_msg(_envelope()))
    patch_io.delete.assert_awaited_once()
    patch_io.slack_deliver.assert_not_called()


async def test_unknown_template_acks(patch_io) -> None:
    await patch_io._handle_message(_msg(_envelope(template="nope")))
    patch_io.delete.assert_awaited_once()
    patch_io.slack_deliver.assert_not_called()


async def test_no_channel_acks(patch_io) -> None:
    patch_io.get_channel_for_org.return_value = None
    await patch_io._handle_message(_msg(_envelope()))
    patch_io.delete.assert_awaited_once()
    patch_io.slack_deliver.assert_not_called()


async def test_unknown_channel_kind_acks(patch_io) -> None:
    await patch_io._handle_message(_msg(_envelope(channel="teams")))
    patch_io.delete.assert_awaited_once()
    patch_io.slack_deliver.assert_not_called()


async def test_permanent_failure_disables_channel(patch_io) -> None:
    patch_io.slack_deliver.return_value = DeliveryResult(
        ok=False, permanent=True, status_code=404
    )
    await patch_io._handle_message(_msg(_envelope()))
    patch_io.disable_channel.assert_awaited_once()
    patch_io.delete.assert_awaited_once()


async def test_transient_failure_does_not_ack(patch_io) -> None:
    patch_io.slack_deliver.return_value = DeliveryResult(
        ok=False, permanent=False, status_code=503
    )
    await patch_io._handle_message(_msg(_envelope()))
    patch_io.delete.assert_not_called()
    patch_io.circuit_breaker.record_failure.assert_awaited_once()
