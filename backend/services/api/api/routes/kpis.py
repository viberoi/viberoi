"""GET /kpis/snapshot — org-level KPI rollup.

For V1, the snapshot is "what we know right now" — live Redis counters
for today plus a simple session count from Postgres. Historical
rollups land when the snapshot cron + Postgres `kpi_snapshots` table
are wired (Slice 7+).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from api.app.auth import ApiAuthContext, require_role
from api.schema.responses import KpiSnapshot
from viberoi_shared.db import org_scoped_session
from viberoi_shared.logging import get_logger
from viberoi_shared.redis.counters import get_today_summary
from viberoi_shared.sessions.models import SessionRow
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()


@router.get("/snapshot", response_model=KpiSnapshot)
async def snapshot_route(
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
    window_days: int = Query(default=30, ge=1, le=365),
) -> KpiSnapshot:
    """Org-wide rollup for the past `window_days`. Same numbers for
    every role — the dashboard renders role-appropriate framing on top."""
    today = await get_today_summary(ctx.org_id)
    async with org_scoped_session(ctx.org_id) as db:
        # All sessions in the window, regardless of viewer role — this is
        # an org-level KPI, not a per-developer feed.
        cutoff_expr = func.now() - func.make_interval(0, 0, 0, window_days)
        agg = await db.execute(
            select(
                func.count(SessionRow.id),
                func.coalesce(func.sum(SessionRow.tokens_input + SessionRow.tokens_output), 0),
                func.coalesce(func.sum(SessionRow.total_cost_usd), 0),
                func.count(func.distinct(SessionRow.developer_id)),
                func.avg(
                    func.extract("epoch", SessionRow.ended_at - SessionRow.started_at)
                ),
            ).where(
                SessionRow.org_id == ctx.org_id,
                SessionRow.started_at >= cutoff_expr,
            )
        )
        row = agg.one()

    total_sessions, total_tokens, total_cost, active_devs, avg_duration_s = row
    avg_int: int | None = int(avg_duration_s) if avg_duration_s is not None else None

    # Hallucination-loop rate not yet computed — placeholder None until the
    # Worker writes per-session `quality_hallucination_risk` consistently
    # (Slice 7).
    return KpiSnapshot(
        window_days=window_days,
        total_sessions=int(total_sessions or 0) + int(today.get("sessions", 0)),
        total_tokens=int(total_tokens or 0),
        total_cost_usd=Decimal(str(total_cost or 0)) + Decimal(str(today.get("cost_usd", 0))),
        active_developers=int(active_devs or 0),
        avg_session_duration_seconds=avg_int,
        hallucination_loop_rate=None,
    )
