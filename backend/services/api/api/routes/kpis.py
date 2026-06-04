"""GET /kpis/snapshot — org-level KPI rollup.

For V1, the snapshot is "what we know right now" — live Redis counters
for today plus a simple session count from Postgres. Historical
rollups land when the snapshot cron + Postgres `kpi_snapshots` table
are wired (Slice 7+).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text

from api.app.auth import ApiAuthContext, require_role
from api.schema.responses import KpiSnapshot
from viberoi_shared.crypto import decrypt_pii
from viberoi_shared.crypto.envelope import EncryptedField
from viberoi_shared.db import org_scoped_session
from viberoi_shared.logging import get_logger
from viberoi_shared.orgs.models import Developer
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


# ── Time series ─────────────────────────────────────────────────────────────


class TimeseriesPoint(BaseModel):
    day: datetime
    sessions: int
    tokens: int
    cost_usd: Decimal


class TimeseriesResponse(BaseModel):
    window_days: int
    points: list[TimeseriesPoint]


@router.get("/timeseries", response_model=TimeseriesResponse)
async def timeseries_route(
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
    window_days: int = Query(default=30, ge=1, le=365),
) -> TimeseriesResponse:
    """Daily rollup of sessions/tokens/cost for the dashboard trend chart.

    Generates a continuous day series so the chart shows zero-days as
    flat points rather than gaps.
    """
    async with org_scoped_session(ctx.org_id) as db:
        rows = await db.execute(
            text(
                """
                WITH days AS (
                  SELECT generate_series(
                    date_trunc('day', now() - make_interval(days => :w - 1)),
                    date_trunc('day', now()),
                    interval '1 day'
                  )::date AS day
                ),
                agg AS (
                  SELECT date_trunc('day', captured_at)::date AS day,
                         COUNT(*) AS sessions,
                         COALESCE(SUM(tokens_input + tokens_output), 0) AS tokens,
                         COALESCE(SUM(total_cost_usd), 0) AS cost_usd
                  FROM sessions
                  WHERE captured_at >= now() - make_interval(days => :w)
                  GROUP BY 1
                )
                SELECT d.day,
                       COALESCE(a.sessions, 0) AS sessions,
                       COALESCE(a.tokens, 0) AS tokens,
                       COALESCE(a.cost_usd, 0) AS cost_usd
                FROM days d
                LEFT JOIN agg a USING (day)
                ORDER BY d.day
                """
            ),
            {"w": window_days},
        )
        points = [
            TimeseriesPoint(
                day=datetime.combine(r[0], datetime.min.time()),
                sessions=int(r[1]),
                tokens=int(r[2]),
                cost_usd=Decimal(str(r[3])),
            )
            for r in rows.all()
        ]
    return TimeseriesResponse(window_days=window_days, points=points)


# ── By developer ────────────────────────────────────────────────────────────


class DeveloperRollup(BaseModel):
    developer_id: str
    email: str
    role: str
    sessions: int
    tokens: int
    cost_usd: Decimal


class ByDeveloperResponse(BaseModel):
    window_days: int
    items: list[DeveloperRollup]


@router.get("/by-developer", response_model=ByDeveloperResponse)
async def by_developer_route(
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD)),
    ],
    window_days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
) -> ByDeveloperResponse:
    """Top developers in the org ranked by session count.

    OrgAdmin + TeamLead only (Developers shouldn't see peer breakdowns).
    Decrypts email for display — N KMS calls, fine for V1 (limit 10).
    """
    async with org_scoped_session(ctx.org_id) as db:
        rows = await db.execute(
            text(
                """
                SELECT d.id, d.role,
                       d.email_ciphertext, d.email_key_version, d.email_iv,
                       COALESCE(COUNT(s.id), 0) AS sessions,
                       COALESCE(SUM(s.tokens_input + s.tokens_output), 0) AS tokens,
                       COALESCE(SUM(s.total_cost_usd), 0) AS cost_usd
                FROM developers d
                LEFT JOIN sessions s
                  ON s.developer_id = d.id
                 AND s.captured_at >= now() - make_interval(days => :w)
                WHERE d.org_id = :org
                GROUP BY d.id, d.role,
                         d.email_ciphertext, d.email_key_version, d.email_iv
                ORDER BY sessions DESC NULLS LAST, cost_usd DESC NULLS LAST
                LIMIT :lim
                """
            ),
            {"w": window_days, "org": str(ctx.org_id), "lim": limit},
        )

        items: list[DeveloperRollup] = []
        for r in rows.all():
            dev_id, role, ct, kv, iv, sessions, tokens, cost = r
            email = await decrypt_pii(
                EncryptedField(
                    ciphertext=bytes(ct), key_version=kv, iv=bytes(iv)
                ),
                context=f"org:{ctx.org_id}:developer:field:email",
            )
            items.append(
                DeveloperRollup(
                    developer_id=str(dev_id),
                    email=email,
                    role=role,
                    sessions=int(sessions),
                    tokens=int(tokens),
                    cost_usd=Decimal(str(cost)),
                )
            )
    return ByDeveloperResponse(window_days=window_days, items=items)
