"""GET /integrations + DELETE /integrations/{provider} route tests.

Orchestrator mocked — only HTTP shape + RBAC under test.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from integration.api import integrations as integrations_routes
from integration.app.auth import IntegrationAuthContext
from viberoi_shared.errors import NotFound


@pytest.fixture
def mock_list(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(
        return_value=[
            {
                "id": uuid4(),
                "provider": "github",
                "installed_by_developer_id": uuid4(),
                "expires_at": datetime.now(tz=UTC),
                "scope": "contents:read",
                "created_at": datetime.now(tz=UTC),
                "webhook_registration_status": "ok",
                "last_sync_at": None,
                "revoked": False,
            },
            {
                "id": uuid4(),
                "provider": "linear",
                "installed_by_developer_id": uuid4(),
                "expires_at": None,
                "scope": "read",
                "created_at": datetime.now(tz=UTC),
                "webhook_registration_status": "failed",
                "last_sync_at": None,
                "revoked": False,
            },
        ]
    )
    monkeypatch.setattr(integrations_routes, "list_integrations", mock)
    return mock


@pytest.fixture
def mock_disconnect(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(integrations_routes, "disconnect", mock)
    return mock


# ── GET /integrations ──────────────────────────────────────────────────────


def test_list_returns_summaries(
    client_as: Callable,
    org_admin_ctx: IntegrationAuthContext,
    mock_list: AsyncMock,
) -> None:
    r = client_as(org_admin_ctx).get("/integrations")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["provider"] == "github"
    assert body[1]["webhook_registration_status"] == "failed"
    mock_list.assert_called_once_with(org_id=org_admin_ctx.org_id)


@pytest.mark.parametrize(
    "ctx_name", ["org_admin_ctx", "team_lead_ctx", "developer_ctx"]
)
def test_list_any_role_can_access(
    client_as: Callable,
    ctx_name: str,
    request: pytest.FixtureRequest,
    mock_list: AsyncMock,  # noqa: ARG001
) -> None:
    ctx = request.getfixturevalue(ctx_name)
    r = client_as(ctx).get("/integrations")
    assert r.status_code == 200


# ── DELETE /integrations/{provider} ───────────────────────────────────────


def test_disconnect_orgadmin_succeeds(
    client_as: Callable,
    org_admin_ctx: IntegrationAuthContext,
    mock_disconnect: AsyncMock,
) -> None:
    r = client_as(org_admin_ctx).delete("/integrations/github")
    assert r.status_code == 204
    mock_disconnect.assert_called_once_with(
        org_id=org_admin_ctx.org_id, provider="github"
    )


@pytest.mark.parametrize("ctx_name", ["team_lead_ctx", "developer_ctx"])
def test_disconnect_non_admin_forbidden(
    client_as: Callable,
    ctx_name: str,
    request: pytest.FixtureRequest,
    mock_disconnect: AsyncMock,
) -> None:
    ctx = request.getfixturevalue(ctx_name)
    r = client_as(ctx).delete("/integrations/jira")
    assert r.status_code == 403
    mock_disconnect.assert_not_called()


def test_disconnect_unknown_integration_returns_404(
    client_as: Callable,
    org_admin_ctx: IntegrationAuthContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        integrations_routes,
        "disconnect",
        AsyncMock(side_effect=NotFound("no integration")),
    )
    r = client_as(org_admin_ctx).delete("/integrations/linear")
    assert r.status_code == 404
