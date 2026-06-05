"""GET /sessions + GET /sessions/{id} — route shape, RBAC, paging.

Repository layer mocked. Hits no DB.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from api.app.auth import ApiAuthContext
from api.routes import sessions as sessions_routes

from viberoi_shared.errors import NotFound
from viberoi_shared.types.enums import Role


def _fake_row(
    *,
    developer_id: UUID | None = None,
    started_at: datetime | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = uuid4()
    row.session_id = f"sess-{row.id.hex[:8]}"
    row.developer_id = developer_id or uuid4()
    row.tool_name = "claude_code"
    row.tool_model = "claude-opus-4-7"
    row.started_at = started_at or datetime.now(tz=UTC)
    row.ended_at = (started_at or datetime.now(tz=UTC)) + timedelta(minutes=20)
    row.tokens_input = 5000
    row.tokens_output = 1000
    row.tokens_cache_read = 0
    row.tokens_cache_write = 0
    row.total_cost_usd = Decimal("0.42")
    row.is_estimated = False
    row.attr_ticket_id = "ABC-42"
    row.attr_signals = ["branch_parse"]
    row.attr_confidence = Decimal("0.85")
    row.attr_method = "signals_v1"
    row.repo_branch = "feature/foo"
    row.repo_name = "demo-repo"
    row.repo_origin_cwd = "/tmp/demo-repo"
    row.schema_version = "1.0"
    row.files_touched_count = 3
    row.files_touched = ["src/a.py", "src/b.py", "src/c.py"]
    row.turn_count = 12
    row.subagent_count = 0
    row.mode = "agent"
    row.is_agentic = True
    row.lines_added = 50
    row.lines_deleted = 10
    row.is_committed = True
    row.commit_hashes = ["abc1234"]
    row.quality_session_restarts = 0
    row.quality_file_oscillations = 0
    return row


# ── GET /sessions ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_list(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    rows = [_fake_row(), _fake_row()]
    mock = AsyncMock(return_value=(rows, "next-cursor-xyz"))
    monkeypatch.setattr(sessions_routes, "list_sessions", mock)
    # Also stub org_scoped_session so we don't touch the DB.
    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(sessions_routes, "org_scoped_session", lambda _: _Ctx())
    return mock


def test_list_orgadmin_gets_all(
    client_as: Callable, org_admin_ctx: ApiAuthContext, mock_list: AsyncMock
) -> None:
    r = client_as(org_admin_ctx).get("/sessions")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] == "next-cursor-xyz"
    kw = mock_list.call_args.kwargs
    assert kw["viewer_role"] == Role.ORG_ADMIN


def test_list_developer_passes_self_id(
    client_as: Callable, developer_ctx: ApiAuthContext, mock_list: AsyncMock
) -> None:
    client_as(developer_ctx).get("/sessions")
    kw = mock_list.call_args.kwargs
    assert kw["viewer_role"] == Role.DEVELOPER
    assert kw["viewer_developer_id"] == developer_ctx.developer_id


def test_list_team_lead_passes_team(
    client_as: Callable, team_lead_ctx: ApiAuthContext, mock_list: AsyncMock
) -> None:
    client_as(team_lead_ctx).get("/sessions")
    kw = mock_list.call_args.kwargs
    assert kw["viewer_role"] == Role.TEAM_LEAD
    assert kw["viewer_team_id"] == team_lead_ctx.team_id


def test_list_forwards_cursor_and_limit(
    client_as: Callable, org_admin_ctx: ApiAuthContext, mock_list: AsyncMock
) -> None:
    client_as(org_admin_ctx).get("/sessions?cursor=abc&limit=10")
    kw = mock_list.call_args.kwargs
    assert kw["cursor"] == "abc"
    assert kw["limit"] == 10


def test_list_rejects_limit_over_cap(
    client_as: Callable, org_admin_ctx: ApiAuthContext, mock_list: AsyncMock
) -> None:
    r = client_as(org_admin_ctx).get("/sessions?limit=999")
    assert r.status_code == 422


def test_list_unauthenticated_401(client) -> None:
    r = client.get("/sessions")
    assert r.status_code in (401, 500)  # 500 if CognitoNotImplemented surfaces


# ── GET /sessions/{id} ─────────────────────────────────────────────────────


@pytest.fixture
def mock_get(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, Any]:
    row = _fake_row()
    mock = AsyncMock(return_value=row)
    monkeypatch.setattr(sessions_routes, "get_by_id", mock)
    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(sessions_routes, "org_scoped_session", lambda _: _Ctx())
    return mock, row


def test_detail_orgadmin_sees_any(
    client_as: Callable, org_admin_ctx: ApiAuthContext, mock_get
) -> None:
    _, row = mock_get
    row.org_id = org_admin_ctx.org_id
    r = client_as(org_admin_ctx).get(f"/sessions/{row.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["external_id"] == row.session_id
    assert body["files_touched_count"] == 3
    assert body["attribution_signals"] == ["branch_parse"]


def test_detail_developer_sees_own_only(
    client_as: Callable, developer_ctx: ApiAuthContext, mock_get
) -> None:
    _, row = mock_get
    row.org_id = developer_ctx.org_id
    # row.developer_id != developer_ctx.developer_id → 404
    r = client_as(developer_ctx).get(f"/sessions/{row.id}")
    assert r.status_code == 404


def test_detail_developer_sees_own(
    client_as: Callable, developer_ctx: ApiAuthContext, mock_get
) -> None:
    mock, row = mock_get
    row.org_id = developer_ctx.org_id
    row.developer_id = developer_ctx.developer_id
    r = client_as(developer_ctx).get(f"/sessions/{row.id}")
    assert r.status_code == 200


def test_detail_team_lead_blocked_if_not_in_team(
    client_as: Callable,
    team_lead_ctx: ApiAuthContext,
    mock_get,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, row = mock_get
    row.org_id = team_lead_ctx.org_id
    dev = MagicMock()
    dev.team_id = uuid4()  # different team
    monkeypatch.setattr(sessions_routes, "get_developer", AsyncMock(return_value=dev))
    r = client_as(team_lead_ctx).get(f"/sessions/{row.id}")
    assert r.status_code == 404


def test_detail_team_lead_allowed_if_in_team(
    client_as: Callable,
    team_lead_ctx: ApiAuthContext,
    mock_get,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, row = mock_get
    row.org_id = team_lead_ctx.org_id
    dev = MagicMock()
    dev.team_id = team_lead_ctx.team_id  # same team
    monkeypatch.setattr(sessions_routes, "get_developer", AsyncMock(return_value=dev))
    r = client_as(team_lead_ctx).get(f"/sessions/{row.id}")
    assert r.status_code == 200


def test_detail_cross_org_blocked(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    mock_get,
) -> None:
    """If RLS somehow returns a row from a different org, the explicit
    org_id check still 404s. Defense in depth."""
    _, row = mock_get
    row.org_id = uuid4()  # different from org_admin_ctx.org_id
    r = client_as(org_admin_ctx).get(f"/sessions/{row.id}")
    assert r.status_code == 404


def test_detail_team_lead_with_no_team_blocked(
    client_as: Callable,
    mock_get,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A TeamLead with team_id=None must NOT see sessions of other
    developers also with team_id=None — matches the list endpoint."""
    from api.app.auth import ApiAuthContext
    from viberoi_shared.types.enums import Role as _Role

    unassigned_lead = ApiAuthContext(
        developer_id=uuid4(),
        org_id=uuid4(),
        role=_Role.TEAM_LEAD,
        team_id=None,
    )
    _, row = mock_get
    row.org_id = unassigned_lead.org_id  # pass the org_id check
    # No team_id setup needed — the lead's None team_id is what we test.
    r = client_as(unassigned_lead).get(f"/sessions/{row.id}")
    assert r.status_code == 404


def test_detail_unknown_id_404(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sessions_routes,
        "get_by_id",
        AsyncMock(side_effect=NotFound("nope")),
    )
    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(sessions_routes, "org_scoped_session", lambda _: _Ctx())
    r = client_as(org_admin_ctx).get(f"/sessions/{uuid4()}")
    assert r.status_code == 404
