"""GET /tickets/{id} — route shape + cross-org guard."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from api.app.auth import ApiAuthContext
from api.routes import tickets as tickets_routes

from viberoi_shared.errors import NotFound


def _fake_ticket(org_id) -> MagicMock:
    t = MagicMock()
    t.id = uuid4()
    t.org_id = org_id
    t.system = "github_issues"
    t.external_id = "viberoi/viberoi#42"
    t.title = "Fix flaky test"
    t.status = "open"
    t.sprint_id = uuid4()
    t.assignee_developer_id = uuid4()
    t.story_points = Decimal("3")
    t.priority = "medium"
    t.created_at_external = datetime.now(tz=UTC)
    t.closed_at_external = None
    return t


@pytest.fixture
def _stub_db(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(tickets_routes, "org_scoped_session", lambda _: _Ctx())


def test_detail_returns_ticket(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    t = _fake_ticket(org_admin_ctx.org_id)
    monkeypatch.setattr(tickets_routes, "get_ticket", AsyncMock(return_value=t))
    r = client_as(org_admin_ctx).get(f"/tickets/{t.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["external_id"] == t.external_id
    assert body["story_points"] == "3"


def test_detail_cross_org_blocked(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    t = _fake_ticket(uuid4())
    monkeypatch.setattr(tickets_routes, "get_ticket", AsyncMock(return_value=t))
    r = client_as(org_admin_ctx).get(f"/tickets/{t.id}")
    assert r.status_code == 404


def test_detail_unknown_404(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    monkeypatch.setattr(
        tickets_routes, "get_ticket", AsyncMock(side_effect=NotFound("nope"))
    )
    r = client_as(org_admin_ctx).get(f"/tickets/{uuid4()}")
    assert r.status_code == 404


# ── GET /tickets/{id}/sessions ────────────────────────────────────────────


def _fake_session_row():
    s = MagicMock()
    s.id = uuid4()
    s.session_id = "sess-1"
    s.developer_id = uuid4()
    s.tool_name = "claude_code"
    s.tool_model = "claude-opus-4-7"
    s.started_at = datetime.now(tz=UTC)
    s.ended_at = datetime.now(tz=UTC)
    s.tokens_input = 1000
    s.tokens_output = 200
    s.total_cost_usd = Decimal("0.42")
    s.attr_ticket_id = "ABC-1"
    s.attr_signals = ["branch_parse"]
    s.repo_branch = "feature/x"
    s.schema_version = "1.0"
    s.files_touched_count = 3
    return s


def test_sessions_for_ticket_returns_list(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    t = _fake_ticket(org_admin_ctx.org_id)
    t.external_id = "ABC-1"
    monkeypatch.setattr(tickets_routes, "get_ticket", AsyncMock(return_value=t))
    monkeypatch.setattr(
        tickets_routes,
        "list_sessions_for_ticket",
        AsyncMock(return_value=[_fake_session_row(), _fake_session_row()]),
    )
    r = client_as(org_admin_ctx).get(f"/tickets/{t.id}/sessions")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    # No paging on this endpoint — next_cursor is always null.
    assert body["next_cursor"] is None


def test_sessions_for_ticket_cross_org_blocked(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    t = _fake_ticket(uuid4())  # different org
    monkeypatch.setattr(tickets_routes, "get_ticket", AsyncMock(return_value=t))
    r = client_as(org_admin_ctx).get(f"/tickets/{t.id}/sessions")
    assert r.status_code == 404
