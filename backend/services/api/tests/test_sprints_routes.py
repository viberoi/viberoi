"""GET /sprints + GET /sprints/{id} — route shape + RBAC."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from api.app.auth import ApiAuthContext
from api.routes import sprints as sprints_routes

from viberoi_shared.errors import NotFound


def _fake_sprint(state: str = "active") -> MagicMock:
    sp = MagicMock()
    sp.id = uuid4()
    sp.org_id = uuid4()
    sp.system = "jira"
    sp.external_id = "42"
    sp.name = "Sprint 42"
    sp.state = state
    sp.started_at = datetime.now(tz=UTC)
    sp.ended_at = None
    sp.completed_at = None
    sp.board_id = "B1"
    return sp


@pytest.fixture
def _stub_db(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(sprints_routes, "org_scoped_session", lambda _: _Ctx())


def test_list_returns_sprints(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    sp = _fake_sprint()
    monkeypatch.setattr(
        sprints_routes,
        "list_sprints_with_counts",
        AsyncMock(return_value=[(sp, 7)]),
    )
    r = client_as(org_admin_ctx).get("/sprints")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["ticket_count"] == 7


def test_list_state_filter_forwarded(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    mock = AsyncMock(return_value=[])
    monkeypatch.setattr(sprints_routes, "list_sprints_with_counts", mock)
    client_as(org_admin_ctx).get("/sprints?state=active&state=future")
    assert mock.call_args.kwargs["include_states"] == ["active", "future"]


def test_detail_returns_sprint(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    sp = _fake_sprint()
    sp.org_id = org_admin_ctx.org_id
    monkeypatch.setattr(sprints_routes, "get_sprint", AsyncMock(return_value=sp))
    monkeypatch.setattr(
        sprints_routes, "count_tickets_for_sprint", AsyncMock(return_value=12)
    )
    r = client_as(org_admin_ctx).get(f"/sprints/{sp.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["ticket_count"] == 12
    assert body["total_cost_usd"] == "0.00"


def test_detail_cross_org_blocked(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    """If RLS somehow let a cross-org row through, the explicit check 404s."""
    sp = _fake_sprint()
    sp.org_id = uuid4()  # different org
    monkeypatch.setattr(sprints_routes, "get_sprint", AsyncMock(return_value=sp))
    r = client_as(org_admin_ctx).get(f"/sprints/{sp.id}")
    assert r.status_code == 404


def test_detail_unknown_id_404(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    monkeypatch.setattr(
        sprints_routes, "get_sprint", AsyncMock(side_effect=NotFound("nope"))
    )
    r = client_as(org_admin_ctx).get(f"/sprints/{uuid4()}")
    assert r.status_code == 404
