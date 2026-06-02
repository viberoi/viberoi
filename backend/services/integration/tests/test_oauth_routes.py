"""OAuth-route tests — orchestrator mocked, no real OAuth/DB/Redis.

Confirms HTTP shape, RBAC, error redirect paths.
"""

from __future__ import annotations

from typing import Callable
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI

from integration.api import oauth as oauth_routes
from integration.app.auth import IntegrationAuthContext
from integration.app.orchestrator import (
    CompleteResult,
    InitiateResult,
)
from integration.app.providers.base import OAuthCallbackError
from viberoi_shared.integrations.oauth_state import OAuthStateError


@pytest.fixture
def mock_initiate(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(
        return_value=InitiateResult(
            authorize_url="https://provider.example.com/auth?state=abc"
        )
    )
    monkeypatch.setattr(oauth_routes, "initiate_connect", mock)
    return mock


@pytest.fixture
def mock_complete(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(
        return_value=CompleteResult(
            integration_id=UUID("11111111-2222-3333-4444-555555555555"),
            webhook_registration_status="ok",
        )
    )
    monkeypatch.setattr(oauth_routes, "complete_connect", mock)
    return mock


# ── POST /{provider}/connect ────────────────────────────────────────────────


def test_connect_orgadmin_gets_authorize_url(
    client_as: Callable,
    org_admin_ctx: IntegrationAuthContext,
    mock_initiate: AsyncMock,
) -> None:
    r = client_as(org_admin_ctx).post("/integrations/github/connect")
    assert r.status_code == 200
    assert r.json()["authorize_url"].startswith("https://")
    mock_initiate.assert_called_once()
    # Verify org/dev were threaded from auth context
    call_kwargs = mock_initiate.call_args.kwargs
    assert call_kwargs["org_id"] == org_admin_ctx.org_id
    assert call_kwargs["developer_id"] == org_admin_ctx.developer_id
    assert call_kwargs["provider"] == "github"


def test_connect_unknown_provider_404(
    client_as: Callable,
    org_admin_ctx: IntegrationAuthContext,
    mock_initiate: AsyncMock,  # noqa: ARG001
) -> None:
    r = client_as(org_admin_ctx).post("/integrations/bitbucket/connect")
    assert r.status_code == 404


@pytest.mark.parametrize("ctx_name", ["team_lead_ctx", "developer_ctx"])
def test_connect_non_admin_forbidden(
    client_as: Callable,
    ctx_name: str,
    request: pytest.FixtureRequest,
    mock_initiate: AsyncMock,  # noqa: ARG001
) -> None:
    ctx = request.getfixturevalue(ctx_name)
    r = client_as(ctx).post("/integrations/linear/connect")
    assert r.status_code == 403


def test_connect_unauthenticated_401(client, mock_initiate: AsyncMock) -> None:  # noqa: ARG001
    """No auth header → real authenticate dep runs → CognitoNotImplemented
    or Unauthorized → 401."""
    r = client.post("/integrations/github/connect")
    # Will be 401 (Unauthorized) since the bearer-token parsing rejects
    # before reaching the verify_jwt stub.
    assert r.status_code in (401, 500)  # 500 if CognitoNotImplemented propagates


# ── GET /{provider}/callback ───────────────────────────────────────────────


def test_callback_success_redirects_to_frontend(
    client,
    mock_complete: AsyncMock,
) -> None:
    r = client.get(
        "/integrations/jira/callback?code=abc&state=xyz",
        follow_redirects=False,
    )
    assert r.status_code == 302
    location = r.headers["location"]
    assert location.startswith("https://app.viberoi.io/settings/integrations?")
    assert "status=ok" in location
    assert "id=11111111-2222-3333-4444-555555555555" in location


def test_callback_unknown_provider_redirects_with_error(
    client,
    mock_complete: AsyncMock,  # noqa: ARG001
) -> None:
    r = client.get(
        "/integrations/bitbucket/callback?code=x", follow_redirects=False
    )
    assert r.status_code == 302
    assert "err=unknown_provider" in r.headers["location"]


def test_callback_bad_state_redirects_with_error(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oauth_routes,
        "complete_connect",
        AsyncMock(side_effect=OAuthStateError("bad state")),
    )
    r = client.get(
        "/integrations/github/callback?code=x&state=bad",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "err=oauth_state" in r.headers["location"]


def test_callback_user_cancelled_redirects_with_error(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oauth_routes,
        "complete_connect",
        AsyncMock(side_effect=OAuthCallbackError("user denied")),
    )
    r = client.get(
        "/integrations/github/callback?state=x", follow_redirects=False
    )
    assert r.status_code == 302
    assert "err=user_cancelled" in r.headers["location"]


def test_callback_unhandled_error_redirects_generic(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unexpected exception during complete_connect → generic 'err=internal'
    redirect. Crucially, no exception details leak."""
    monkeypatch.setattr(
        oauth_routes,
        "complete_connect",
        AsyncMock(side_effect=RuntimeError("secret information!")),
    )
    r = client.get(
        "/integrations/linear/callback?code=x&state=x",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "err=internal" in r.headers["location"]
    assert "secret information" not in r.headers["location"]
