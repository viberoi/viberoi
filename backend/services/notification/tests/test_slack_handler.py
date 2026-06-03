"""Slack-handler tests against a mocked httpx transport."""

from __future__ import annotations

import httpx
import pytest
import respx

from notification.app.handlers.slack import deliver
from notification.app.templates import SlackPayload

WEBHOOK_URL = "https://hooks.slack.com/services/T/B/X"


def _payload() -> SlackPayload:
    return SlackPayload(text="hi", blocks=[{"type": "section"}])


@pytest.mark.respx(base_url="https://hooks.slack.com")
async def test_200_is_ok(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/services/T/B/X").mock(return_value=httpx.Response(200))
    result = await deliver(webhook_url=WEBHOOK_URL, payload=_payload())
    assert result.ok is True
    assert result.permanent is False
    assert result.status_code == 200


@pytest.mark.respx(base_url="https://hooks.slack.com")
async def test_429_is_transient(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/services/T/B/X").mock(return_value=httpx.Response(429))
    result = await deliver(webhook_url=WEBHOOK_URL, payload=_payload())
    assert result.ok is False
    assert result.permanent is False


@pytest.mark.respx(base_url="https://hooks.slack.com")
async def test_500_is_transient(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/services/T/B/X").mock(return_value=httpx.Response(503))
    result = await deliver(webhook_url=WEBHOOK_URL, payload=_payload())
    assert result.ok is False
    assert result.permanent is False


@pytest.mark.respx(base_url="https://hooks.slack.com")
async def test_404_is_permanent(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/services/T/B/X").mock(return_value=httpx.Response(404))
    result = await deliver(webhook_url=WEBHOOK_URL, payload=_payload())
    assert result.ok is False
    assert result.permanent is True


@pytest.mark.respx(base_url="https://hooks.slack.com")
async def test_403_is_permanent(respx_mock: respx.MockRouter) -> None:
    """Slack returns 403 for revoked / disabled webhook URLs."""
    respx_mock.post("/services/T/B/X").mock(return_value=httpx.Response(403))
    result = await deliver(webhook_url=WEBHOOK_URL, payload=_payload())
    assert result.ok is False
    assert result.permanent is True


@pytest.mark.respx(base_url="https://hooks.slack.com")
async def test_network_error_is_transient(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/services/T/B/X").mock(side_effect=httpx.ConnectError("boom"))
    result = await deliver(webhook_url=WEBHOOK_URL, payload=_payload())
    assert result.ok is False
    assert result.permanent is False
