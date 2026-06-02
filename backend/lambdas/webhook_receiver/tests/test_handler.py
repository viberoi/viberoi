"""Webhook receiver Lambda — unit tests with mocked dependencies."""

from __future__ import annotations

import base64
import hashlib
import hmac
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from webhook_receiver import handler as handler_mod

_SECRET = b"test-webhook-secret"
_CONTEXT = SimpleNamespace(aws_request_id="lambda-test-req")


def _gh_sig(body: bytes, secret: bytes = _SECRET) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def _apigw_event(
    *,
    path: str,
    body: bytes,
    headers: dict[str, str] | None = None,
    is_base64: bool = False,
) -> dict[str, Any]:
    encoded_body = (
        base64.b64encode(body).decode("ascii") if is_base64 else body.decode("utf-8")
    )
    return {
        "version": "2.0",
        "rawPath": path,
        "requestContext": {"http": {"method": "POST", "path": path}},
        "headers": headers or {},
        "body": encoded_body,
        "isBase64Encoded": is_base64,
    }


@pytest.fixture
def integration_id() -> UUID:
    return uuid4()


@pytest.fixture
def org_id() -> UUID:
    return uuid4()


@pytest.fixture
def patch_creds(
    monkeypatch: pytest.MonkeyPatch, integration_id: UUID, org_id: UUID
) -> None:
    """Mock the DB lookup so the test doesn't need Postgres."""

    async def _fake(integration_uuid: UUID, provider: str):
        if integration_uuid != integration_id:
            return None
        return (org_id, _SECRET)

    monkeypatch.setattr(handler_mod, "get_webhook_credentials", _fake)


@pytest.fixture
def patch_sqs(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Mock the SQS publish call; return the AsyncMock for assertions."""
    mock = AsyncMock(return_value="message-id-123")
    monkeypatch.setattr(handler_mod, "sqs_publish", mock)
    return mock


# ── Happy paths ─────────────────────────────────────────────────────────────


def test_valid_github_webhook_publishes_to_sqs(
    integration_id: UUID,
    org_id: UUID,
    patch_creds: None,
    patch_sqs: AsyncMock,
) -> None:
    body = b'{"action":"opened"}'
    event = _apigw_event(
        path=f"/webhooks/github/{integration_id}",
        body=body,
        headers={
            "X-Hub-Signature-256": _gh_sig(body),
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "deliv-1",
            "User-Agent": "GitHub-Hookshot/abc",
            "X-Random-Header": "should-be-filtered",
        },
    )
    response = handler_mod.handler(event, _CONTEXT)
    assert response["statusCode"] == 200

    assert patch_sqs.await_count == 1
    queue, payload = patch_sqs.await_args.args
    assert queue == "webhook_events"
    assert payload["org_id"] == str(org_id)
    assert payload["provider"] == "github"
    assert payload["delivery_id"] == "deliv-1"
    # body_b64 should decode back to the original
    assert base64.b64decode(payload["body_b64"]) == body
    # Random header should NOT appear in forwarded headers
    forwarded = {k.lower() for k in payload["headers"].keys()}
    assert "x-github-event" in forwarded
    assert "x-random-header" not in forwarded


def test_base64_encoded_body_is_decoded(
    integration_id: UUID,
    patch_creds: None,
    patch_sqs: AsyncMock,
) -> None:
    body = b"\x01\x02\x03binary"
    event = _apigw_event(
        path=f"/webhooks/github/{integration_id}",
        body=body,
        headers={"X-Hub-Signature-256": _gh_sig(body)},
        is_base64=True,
    )
    response = handler_mod.handler(event, _CONTEXT)
    assert response["statusCode"] == 200
    payload = patch_sqs.await_args.args[1]
    assert base64.b64decode(payload["body_b64"]) == body


# ── Rejections ──────────────────────────────────────────────────────────────


def test_malformed_path_returns_404(
    integration_id: UUID, patch_creds: None, patch_sqs: AsyncMock
) -> None:
    body = b"body"
    event = _apigw_event(
        path="/webhooks/bitbucket/some-uuid",  # bitbucket not supported
        body=body,
        headers={"X-Hub-Signature-256": _gh_sig(body)},
    )
    response = handler_mod.handler(event, _CONTEXT)
    assert response["statusCode"] == 404
    assert patch_sqs.await_count == 0


def test_invalid_uuid_in_path_returns_404(
    patch_creds: None, patch_sqs: AsyncMock
) -> None:
    event = _apigw_event(
        path="/webhooks/github/not-a-uuid",
        body=b"body",
        headers={"X-Hub-Signature-256": "sha256=abc"},
    )
    response = handler_mod.handler(event, _CONTEXT)
    assert response["statusCode"] == 404


def test_missing_integration_returns_404(
    org_id: UUID, patch_sqs: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake(integration_uuid: UUID, provider: str) -> None:
        return None  # Not found

    monkeypatch.setattr(handler_mod, "get_webhook_credentials", _fake)

    body = b"body"
    event = _apigw_event(
        path=f"/webhooks/github/{uuid4()}",
        body=body,
        headers={"X-Hub-Signature-256": _gh_sig(body)},
    )
    response = handler_mod.handler(event, _CONTEXT)
    assert response["statusCode"] == 404


def test_wrong_signature_returns_401(
    integration_id: UUID, patch_creds: None, patch_sqs: AsyncMock
) -> None:
    body = b"body"
    bad_sig = _gh_sig(body, b"different-secret")
    event = _apigw_event(
        path=f"/webhooks/github/{integration_id}",
        body=body,
        headers={"X-Hub-Signature-256": bad_sig},
    )
    response = handler_mod.handler(event, _CONTEXT)
    assert response["statusCode"] == 401
    assert patch_sqs.await_count == 0


def test_get_method_returns_401(
    integration_id: UUID, patch_creds: None, patch_sqs: AsyncMock
) -> None:
    """API Gateway sanity check — only POST is allowed."""
    event = _apigw_event(
        path=f"/webhooks/github/{integration_id}",
        body=b"body",
        headers={},
    )
    event["requestContext"]["http"]["method"] = "GET"
    response = handler_mod.handler(event, _CONTEXT)
    assert response["statusCode"] == 401


def test_non_v2_event_returns_401(
    integration_id: UUID, patch_creds: None, patch_sqs: AsyncMock
) -> None:
    event = _apigw_event(
        path=f"/webhooks/github/{integration_id}",
        body=b"body",
        headers={},
    )
    event["version"] = "1.0"
    response = handler_mod.handler(event, _CONTEXT)
    assert response["statusCode"] == 401


def test_unhandled_exception_returns_500(
    integration_id: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If something blows up unexpectedly, return 500 (not 200) so the
    provider retries instead of marking the delivery successful."""

    async def _fake(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(handler_mod, "get_webhook_credentials", _fake)

    body = b"body"
    event = _apigw_event(
        path=f"/webhooks/github/{integration_id}",
        body=body,
        headers={"X-Hub-Signature-256": _gh_sig(body)},
    )
    response = handler_mod.handler(event, _CONTEXT)
    assert response["statusCode"] == 500
    # Generic body — must NOT leak the exception message
    assert "boom" not in response["body"]
