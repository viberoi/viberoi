"""Linear provider tests — respx-mocked GraphQL + REST."""

from __future__ import annotations

import httpx
import orjson
import pytest
import respx

from integration.app import http_client
from integration.app.providers.base import (
    OAuthCallbackError,
    ProviderConnection,
    TokenRefreshError,
    WebhookRegistrationError,
)
from integration.app.providers.linear import LinearAdapter


@pytest.fixture
def adapter() -> LinearAdapter:
    return LinearAdapter(client_id="cid", client_secret="csec")  # noqa: S106


@pytest.fixture(autouse=True)
async def _reset() -> None:
    await http_client.aclose()
    yield
    await http_client.aclose()


# ── authorize_url ───────────────────────────────────────────────────────────


def test_authorize_url_uses_actor_app(adapter: LinearAdapter) -> None:
    """Per doc-verify 2026-06-03: `actor=application` is deprecated; use `actor=app`."""
    url = adapter.authorize_url(state="abc", redirect_uri="https://x/cb")
    assert url.startswith("https://linear.app/oauth/authorize?")
    assert "actor=app" in url
    assert "actor=application" not in url
    assert "scope=read" in url
    assert "state=abc" in url
    assert "client_id=cid" in url


# ── complete_callback ───────────────────────────────────────────────────────


@pytest.mark.respx(base_url="https://api.linear.app")
async def test_complete_callback_exchanges_code(
    adapter: LinearAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post("/oauth/token").respond(
        200,
        json={
            "access_token": "lin_at_123",
            "refresh_token": "lin_rt_456",
            "expires_in": 86400,
            "scope": "read",
            "token_type": "Bearer",
        },
    )
    conn = await adapter.complete_callback(
        {"code": "abc", "state": "x"}, redirect_uri="https://x/cb"
    )
    assert conn.access_token == "lin_at_123"
    assert conn.refresh_token == "lin_rt_456"
    assert conn.expires_at is not None
    assert conn.scope == "read"


async def test_complete_callback_missing_code(adapter: LinearAdapter) -> None:
    with pytest.raises(OAuthCallbackError):
        await adapter.complete_callback({}, redirect_uri="x")


@pytest.mark.respx(base_url="https://api.linear.app")
async def test_complete_callback_bad_credentials_raises(
    adapter: LinearAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post("/oauth/token").respond(
        400, json={"error": "invalid_client"}
    )
    with pytest.raises(TokenRefreshError):
        await adapter.complete_callback({"code": "x"}, redirect_uri="x")


# ── refresh ────────────────────────────────────────────────────────────────


@pytest.mark.respx(base_url="https://api.linear.app")
async def test_refresh_uses_refresh_token(
    adapter: LinearAdapter, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post("/oauth/token").respond(
        200,
        json={
            "access_token": "lin_at_NEW",
            "refresh_token": "lin_rt_NEW",
            "expires_in": 86400,
            "token_type": "Bearer",
        },
    )
    old = ProviderConnection(
        access_token="lin_at_OLD",
        refresh_token="lin_rt_OLD",
    )
    new = await adapter.refresh(old)
    assert new.access_token == "lin_at_NEW"
    assert new.refresh_token == "lin_rt_NEW"

    # Confirm grant_type=refresh_token sent in body
    body = route.calls.last.request.content.decode("utf-8")
    assert "grant_type=refresh_token" in body
    assert "refresh_token=lin_rt_OLD" in body


async def test_refresh_without_token_raises(adapter: LinearAdapter) -> None:
    with pytest.raises(TokenRefreshError):
        await adapter.refresh(ProviderConnection(access_token="x", refresh_token=None))


# ── discover (GraphQL) ─────────────────────────────────────────────────────


@pytest.mark.respx(base_url="https://api.linear.app")
async def test_discover_returns_viewer_and_org(
    adapter: LinearAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post("/graphql").respond(
        200,
        json={
            "data": {
                "viewer": {"id": "u1", "name": "Adnan"},
                "organization": {"id": "o1", "name": "Acme", "urlKey": "acme"},
                "teams": {"nodes": [{"id": "t1", "key": "ENG", "name": "Engineering"}]},
            }
        },
    )
    result = await adapter.discover(ProviderConnection(access_token="t"))
    assert result["data"]["organization"]["urlKey"] == "acme"
    assert len(result["data"]["teams"]["nodes"]) == 1


# ── webhook registration ──────────────────────────────────────────────────


@pytest.mark.respx(base_url="https://api.linear.app")
async def test_register_webhook_succeeds(
    adapter: LinearAdapter, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post("/graphql").respond(
        200,
        json={
            "data": {
                "webhookCreate": {
                    "success": True,
                    "webhook": {"id": "wh_abc"},
                }
            }
        },
    )
    result = await adapter.register_webhook(
        ProviderConnection(access_token="t"),
        webhook_url="https://hooks.viberoi.io/webhooks/linear/uuid",
        secret="rand-secret",
    )
    assert result.provider_webhook_ids == ["wh_abc"]
    assert result.secret == "rand-secret"

    # Confirm mutation body shape
    body = orjson.loads(route.calls.last.request.content)
    assert "webhookCreate" in body["query"]
    variables = body["variables"]["input"]
    assert variables["url"] == "https://hooks.viberoi.io/webhooks/linear/uuid"
    assert variables["secret"] == "rand-secret"
    assert "Issue" in variables["resourceTypes"]
    assert variables["allPublicTeams"] is True


@pytest.mark.respx(base_url="https://api.linear.app")
async def test_register_webhook_unsuccessful_raises(
    adapter: LinearAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post("/graphql").respond(
        200,
        json={"data": {"webhookCreate": {"success": False, "webhook": None}}},
    )
    with pytest.raises(WebhookRegistrationError):
        await adapter.register_webhook(
            ProviderConnection(access_token="t"),
            webhook_url="https://x",
            secret="s",
        )


# ── revoke + delete_webhook ────────────────────────────────────────────────


@pytest.mark.respx(base_url="https://api.linear.app")
async def test_revoke_calls_oauth_revoke(
    adapter: LinearAdapter, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post("/oauth/revoke").respond(200)
    await adapter.revoke(ProviderConnection(access_token="t"))
    body = route.calls.last.request.content.decode("utf-8")
    assert "token=t" in body
    assert "client_id=cid" in body


@pytest.mark.respx(base_url="https://api.linear.app")
async def test_delete_webhook_calls_mutation(
    adapter: LinearAdapter, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post("/graphql").respond(
        200, json={"data": {"webhookDelete": {"success": True}}}
    )
    await adapter.delete_webhook(ProviderConnection(access_token="t"), "wh_id")
    body = orjson.loads(route.calls.last.request.content)
    assert "webhookDelete" in body["query"]
    assert body["variables"]["id"] == "wh_id"


@pytest.mark.respx(base_url="https://api.linear.app")
async def test_revoke_swallows_errors(
    adapter: LinearAdapter, respx_mock: respx.MockRouter
) -> None:
    """A failed revoke shouldn't block local revocation."""
    respx_mock.post("/oauth/revoke").mock(side_effect=httpx.ConnectError("down"))
    # Should not raise
    await adapter.revoke(ProviderConnection(access_token="t"))
