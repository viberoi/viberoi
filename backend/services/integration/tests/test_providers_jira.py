"""Jira provider tests — respx-mocked Atlassian endpoints."""

from __future__ import annotations

import orjson
import pytest
import respx
from integration.app import http_client
from integration.app.providers.base import (
    OAuthCallbackError,
    ProviderConnection,
    ProviderError,
    TokenRefreshError,
    WebhookRegistrationError,
)
from integration.app.providers.jira import JiraAdapter


@pytest.fixture
def adapter() -> JiraAdapter:
    return JiraAdapter(client_id="cid", client_secret="csec")


@pytest.fixture(autouse=True)
async def _reset() -> None:
    await http_client.aclose()
    yield
    await http_client.aclose()


# ── authorize_url ───────────────────────────────────────────────────────────


def test_authorize_url_includes_offline_access_scope(adapter: JiraAdapter) -> None:
    """offline_access is mandatory — without it we get no refresh token."""
    url = adapter.authorize_url(state="abc", redirect_uri="https://x/cb")
    assert url.startswith("https://auth.atlassian.com/authorize?")
    assert "offline_access" in url
    assert "read%3Ajira-work" in url
    assert "audience=api.atlassian.com" in url
    assert "prompt=consent" in url


# ── complete_callback + discovery ──────────────────────────────────────────


@pytest.mark.respx
async def test_complete_callback_exchanges_and_discovers(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    cloud_id = "11111111-2222-3333-4444-555555555555"
    respx_mock.post("https://auth.atlassian.com/oauth/token").respond(
        200,
        json={
            "access_token": "jira_at_123",
            "refresh_token": "jira_rt_456",
            "expires_in": 3600,
            "scope": "read:jira-work read:jira-user offline_access",
            "token_type": "Bearer",
        },
    )
    respx_mock.get(
        "https://api.atlassian.com/oauth/token/accessible-resources"
    ).respond(
        200,
        json=[
            {
                "id": cloud_id,
                "name": "Acme Jira",
                "url": "https://acme.atlassian.net",
                "scopes": ["read:jira-work"],
            }
        ],
    )
    respx_mock.get(
        f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/field"
    ).respond(
        200,
        json=[
            {"id": "summary", "name": "Summary", "custom": False},
            {"id": "customfield_10020", "name": "Sprint", "custom": True},
        ],
    )

    conn = await adapter.complete_callback(
        {"code": "abc", "state": "x"}, redirect_uri="https://x/cb"
    )
    assert conn.access_token == "jira_at_123"
    assert conn.refresh_token == "jira_rt_456"
    assert conn.extra["cloud_id"] == cloud_id
    assert conn.extra["sprint_field_id"] == "customfield_10020"


async def test_complete_callback_missing_code(adapter: JiraAdapter) -> None:
    with pytest.raises(OAuthCallbackError):
        await adapter.complete_callback({}, redirect_uri="x")


@pytest.mark.respx
async def test_complete_callback_no_resources_raises(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post("https://auth.atlassian.com/oauth/token").respond(
        200,
        json={
            "access_token": "t",
            "refresh_token": "r",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
    )
    respx_mock.get(
        "https://api.atlassian.com/oauth/token/accessible-resources"
    ).respond(200, json=[])
    with pytest.raises(ProviderError):
        await adapter.complete_callback({"code": "x"}, redirect_uri="x")


# ── refresh (rotation) ─────────────────────────────────────────────────────


@pytest.mark.respx
async def test_refresh_persists_new_refresh_token(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    """Atlassian rotates refresh tokens on each use."""
    route = respx_mock.post("https://auth.atlassian.com/oauth/token").respond(
        200,
        json={
            "access_token": "at_NEW",
            "refresh_token": "rt_NEW_ROTATED",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
    )
    old = ProviderConnection(
        access_token="at_OLD",
        refresh_token="rt_OLD",
        extra={"cloud_id": "cloud-1", "sprint_field_id": "customfield_10020"},
    )
    new = await adapter.refresh(old)
    assert new.access_token == "at_NEW"
    assert new.refresh_token == "rt_NEW_ROTATED"
    # Discovery metadata preserved across refresh
    assert new.extra["cloud_id"] == "cloud-1"
    assert new.extra["sprint_field_id"] == "customfield_10020"

    body = route.calls.last.request.content.decode("utf-8")
    assert "grant_type=refresh_token" in body
    assert "refresh_token=rt_OLD" in body


async def test_refresh_without_refresh_token_raises(
    adapter: JiraAdapter,
) -> None:
    with pytest.raises(TokenRefreshError):
        await adapter.refresh(
            ProviderConnection(access_token="x", refresh_token=None)
        )


@pytest.mark.respx
async def test_refresh_failure_raises_token_refresh_error(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post("https://auth.atlassian.com/oauth/token").respond(401)
    with pytest.raises(TokenRefreshError):
        await adapter.refresh(
            ProviderConnection(access_token="x", refresh_token="r")
        )


# ── Webhook registration ──────────────────────────────────────────────────


@pytest.mark.respx
async def test_register_webhook_returns_ids(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    cloud_id = "c-1"
    route = respx_mock.post(
        f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/webhook"
    ).respond(
        200,
        json={
            "webhookRegistrationResult": [
                {"createdWebhookId": 42, "errors": None}
            ]
        },
    )
    conn = ProviderConnection(
        access_token="t",
        extra={"cloud_id": cloud_id, "sprint_field_id": "customfield_10020"},
    )
    result = await adapter.register_webhook(
        conn,
        webhook_url="https://hooks.viberoi.io/webhooks/jira/uuid",
        secret="discarded",
    )
    assert result.provider_webhook_ids == ["42"]
    # Jira OAuth 2.0 webhooks don't use HMAC secrets — we surface an empty
    # secret to document this to the storage layer.
    assert result.secret == ""

    body = orjson.loads(route.calls.last.request.content)
    assert body["url"] == "https://hooks.viberoi.io/webhooks/jira/uuid"
    assert "jira:issue_created" in body["webhooks"][0]["events"]


@pytest.mark.respx
async def test_register_webhook_without_cloud_id_raises(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    with pytest.raises(WebhookRegistrationError):
        await adapter.register_webhook(
            ProviderConnection(access_token="t", extra={}),
            webhook_url="https://x",
            secret="s",
        )


@pytest.mark.respx
async def test_register_webhook_all_errors_raises(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    cloud_id = "c-1"
    respx_mock.post(
        f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/webhook"
    ).respond(
        200,
        json={
            "webhookRegistrationResult": [
                {"createdWebhookId": None, "errors": ["INVALID_JQL"]}
            ]
        },
    )
    with pytest.raises(WebhookRegistrationError):
        await adapter.register_webhook(
            ProviderConnection(access_token="t", extra={"cloud_id": cloud_id}),
            webhook_url="https://x",
            secret="s",
        )


# ── revoke / refresh webhooks ──────────────────────────────────────────────


@pytest.mark.respx
async def test_refresh_webhooks_calls_put(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    cloud_id = "c-1"
    route = respx_mock.put(
        f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/webhook/refresh"
    ).respond(200, json={})
    await adapter.refresh_webhooks(
        ProviderConnection(access_token="t", extra={"cloud_id": cloud_id}),
        ["42", "43"],
    )
    body = orjson.loads(route.calls.last.request.content)
    assert body == {"webhookIds": [42, 43]}


@pytest.mark.respx
async def test_revoke_deletes_registered_webhooks(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    cloud_id = "c-1"
    route = respx_mock.delete(
        f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/webhook"
    ).respond(202)
    await adapter.revoke(
        ProviderConnection(
            access_token="t",
            extra={"cloud_id": cloud_id, "webhook_ids": ["42", "43"]},
        )
    )
    body = orjson.loads(route.calls.last.request.content)
    assert body == {"webhookIds": [42, 43]}


@pytest.mark.respx
async def test_revoke_without_state_is_noop(
    adapter: JiraAdapter, respx_mock: respx.MockRouter
) -> None:
    """No cloud_id / webhook_ids → nothing to clean up."""
    await adapter.revoke(ProviderConnection(access_token="t", extra={}))
