"""GET /kpis/snapshot — Redis + Postgres rollup."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from api.app.auth import ApiAuthContext
from api.routes import kpis as kpis_routes


@pytest.fixture
def _stub(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Mock Redis counters + DB execute. The route's SQL goes through a
    SQLAlchemy MagicMock; we just verify the response shape comes out
    right."""
    today_mock = AsyncMock(return_value={"day": "2026-06-03", "sessions": 4, "cost_usd": 1.25})
    monkeypatch.setattr(kpis_routes, "get_today_summary", today_mock)

    fake_row = (100, 250_000, Decimal("42.50"), 7, 1800.0)
    fake_result = MagicMock()
    fake_result.one = MagicMock(return_value=fake_row)
    db_exec = AsyncMock(return_value=fake_result)

    class _DB:
        execute = db_exec

    class _Ctx:
        async def __aenter__(self):
            return _DB()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(kpis_routes, "org_scoped_session", lambda _: _Ctx())
    return {"today": today_mock, "db_exec": db_exec, "row": fake_row}


def test_snapshot_returns_rollup(
    client_as: Callable, org_admin_ctx: ApiAuthContext, _stub
) -> None:
    r = client_as(org_admin_ctx).get("/kpis/snapshot")
    assert r.status_code == 200
    body = r.json()
    # 100 DB sessions + 4 from today's Redis counter
    assert body["total_sessions"] == 104
    assert body["total_tokens"] == 250_000
    # 42.50 + 1.25 = 43.75 — Pydantic serializes Decimal as a string by default
    assert body["total_cost_usd"] == "43.75"
    assert body["active_developers"] == 7
    assert body["avg_session_duration_seconds"] == 1800
    assert body["window_days"] == 30
    assert body["hallucination_loop_rate"] is None


def test_snapshot_custom_window(
    client_as: Callable, org_admin_ctx: ApiAuthContext, _stub
) -> None:
    r = client_as(org_admin_ctx).get("/kpis/snapshot?window_days=7")
    assert r.status_code == 200
    assert r.json()["window_days"] == 7


def test_snapshot_window_too_big_422(
    client_as: Callable, org_admin_ctx: ApiAuthContext, _stub
) -> None:
    r = client_as(org_admin_ctx).get("/kpis/snapshot?window_days=999")
    assert r.status_code == 422
