"""GET /me/* — caller's personal data only.

Per Master spec S-07 "My Activity": every authenticated role (Developer
included) can hit these routes. They ALWAYS scope to `ctx.developer_id`
— even for OrgAdmin / TeamLead. If an admin wants org-wide data they
use /sessions or /kpis/*.

Privacy: developers should be able to see their own sessions WITHOUT
exposing teammate data. RLS already scopes to org; here we add a
hard developer_id filter on top so the org-wide picture is impossible
through this surface.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text

from api.app.auth import ApiAuthContext, require_role
from api.app.session_view import to_summary
from api.schema.responses import SessionListResponse
from viberoi_shared.db import org_scoped_session
from viberoi_shared.logging import get_logger
from viberoi_shared.sessions import list_sessions
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()


# ── /me/sessions ───────────────────────────────────────────────────────────


@router.get("/sessions", response_model=SessionListResponse)
async def my_sessions_route(
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> SessionListResponse:
    """Caller's own sessions, paginated. Always developer-scoped — admins
    don't get a wider view through this endpoint."""
    async with org_scoped_session(ctx.org_id) as db:
        rows, next_cursor = await list_sessions(
            db,
            org_uuid=ctx.org_id,
            viewer_role=Role.DEVELOPER,
            viewer_developer_id=ctx.developer_id,
            viewer_team_id=ctx.team_id,
            cursor=cursor,
            limit=limit,
        )
    return SessionListResponse(
        items=[to_summary(r) for r in rows],
        next_cursor=next_cursor,
    )


# ── /me/summary ────────────────────────────────────────────────────────────


class ToolMix(BaseModel):
    tool_name: str
    sessions: int
    cost_usd: Decimal


class ModelMix(BaseModel):
    model: str
    sessions: int
    cost_usd: Decimal


class ModeMix(BaseModel):
    mode: str
    sessions: int


class TopTicket(BaseModel):
    ticket_external_id: str
    sessions: int
    cost_usd: Decimal


class MeSummary(BaseModel):
    window_days: int
    sessions: int
    tokens: int
    cost_usd: Decimal
    lines_added: int
    lines_deleted: int
    commit_count: int
    avg_session_duration_seconds: int | None
    last_session_at: datetime | None
    tool_mix: list[ToolMix]
    model_mix: list[ModelMix]
    mode_mix: list[ModeMix]
    top_tickets: list[TopTicket]


@router.get("/summary", response_model=MeSummary)
async def my_summary_route(
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
    window_days: int = Query(default=30, ge=1, le=365),
) -> MeSummary:
    """My personal rollup over the window: sessions/tokens/cost, LOC,
    commits, plus per-tool/model/mode breakdowns and top tickets."""
    dev = str(ctx.developer_id)
    async with org_scoped_session(ctx.org_id) as db:
        # Headline numbers.
        head = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*),
                           COALESCE(SUM(tokens_input + tokens_output), 0),
                           COALESCE(SUM(total_cost_usd), 0),
                           COALESCE(SUM(lines_added), 0),
                           COALESCE(SUM(lines_deleted), 0),
                           COALESCE(SUM(COALESCE(array_length(commit_hashes, 1), 0)), 0),
                           COALESCE(AVG(EXTRACT(EPOCH FROM (ended_at - started_at))), NULL),
                           MAX(started_at)
                    FROM sessions
                    WHERE developer_id = :dev
                      AND captured_at >= now() - make_interval(days => :w)
                    """
                ),
                {"dev": dev, "w": window_days},
            )
        ).first()
        sessions = int(head[0] or 0)
        tokens = int(head[1] or 0)
        cost = Decimal(str(head[2] or 0))
        lines_added = int(head[3] or 0)
        lines_deleted = int(head[4] or 0)
        commit_count = int(head[5] or 0)
        avg_dur = int(head[6]) if head[6] is not None else None
        last_session_at = head[7]

        tool_rows = await db.execute(
            text(
                """
                SELECT tool_name, COUNT(*), COALESCE(SUM(total_cost_usd), 0)
                FROM sessions
                WHERE developer_id = :dev
                  AND captured_at >= now() - make_interval(days => :w)
                GROUP BY tool_name
                ORDER BY 3 DESC
                """
            ),
            {"dev": dev, "w": window_days},
        )
        tool_mix = [
            ToolMix(tool_name=r[0], sessions=int(r[1]), cost_usd=Decimal(str(r[2])))
            for r in tool_rows.all()
        ]

        model_rows = await db.execute(
            text(
                """
                SELECT tool_model, COUNT(*), COALESCE(SUM(total_cost_usd), 0)
                FROM sessions
                WHERE developer_id = :dev
                  AND captured_at >= now() - make_interval(days => :w)
                  AND tool_model IS NOT NULL
                GROUP BY tool_model
                ORDER BY 3 DESC
                """
            ),
            {"dev": dev, "w": window_days},
        )
        model_mix = [
            ModelMix(model=r[0], sessions=int(r[1]), cost_usd=Decimal(str(r[2])))
            for r in model_rows.all()
        ]

        mode_rows = await db.execute(
            text(
                """
                SELECT mode, COUNT(*)
                FROM sessions
                WHERE developer_id = :dev
                  AND captured_at >= now() - make_interval(days => :w)
                GROUP BY mode
                ORDER BY 2 DESC
                """
            ),
            {"dev": dev, "w": window_days},
        )
        mode_mix = [
            ModeMix(mode=r[0], sessions=int(r[1])) for r in mode_rows.all()
        ]

        ticket_rows = await db.execute(
            text(
                """
                SELECT attr_ticket_id, COUNT(*), COALESCE(SUM(total_cost_usd), 0)
                FROM sessions
                WHERE developer_id = :dev
                  AND attr_ticket_id IS NOT NULL
                  AND captured_at >= now() - make_interval(days => :w)
                GROUP BY attr_ticket_id
                ORDER BY 3 DESC
                LIMIT 5
                """
            ),
            {"dev": dev, "w": window_days},
        )
        top_tickets = [
            TopTicket(
                ticket_external_id=r[0],
                sessions=int(r[1]),
                cost_usd=Decimal(str(r[2])),
            )
            for r in ticket_rows.all()
        ]

    return MeSummary(
        window_days=window_days,
        sessions=sessions,
        tokens=tokens,
        cost_usd=cost,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        commit_count=commit_count,
        avg_session_duration_seconds=avg_dur,
        last_session_at=last_session_at,
        tool_mix=tool_mix,
        model_mix=model_mix,
        mode_mix=mode_mix,
        top_tickets=top_tickets,
    )
