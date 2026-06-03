"""Sprint list + detail.

  GET /sprints           — all sprints in the org with ticket counts
  GET /sprints/{id}      — sprint + ticket count + cost rollup
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.app.auth import ApiAuthContext, require_role
from api.schema.responses import SprintDetail, SprintListResponse, SprintSummary
from viberoi_shared.db import org_scoped_session
from viberoi_shared.errors import NotFound
from viberoi_shared.logging import get_logger
from viberoi_shared.tickets import (
    count_tickets_for_sprint,
    get_sprint,
    list_sprints_with_counts,
)
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()


def _summary(sp, ticket_count: int) -> SprintSummary:
    return SprintSummary(
        id=sp.id,
        system=sp.system,
        external_id=sp.external_id,
        name=sp.name,
        state=sp.state,
        started_at=sp.started_at,
        ended_at=sp.ended_at,
        completed_at=sp.completed_at,
        board_id=sp.board_id,
        ticket_count=ticket_count,
    )


@router.get("", response_model=SprintListResponse)
async def list_route(
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
    state: list[str] | None = Query(default=None),
) -> SprintListResponse:
    async with org_scoped_session(ctx.org_id) as db:
        rows = await list_sprints_with_counts(
            db, ctx.org_id, include_states=state
        )
    return SprintListResponse(items=[_summary(sp, cnt) for sp, cnt in rows])


@router.get("/{sprint_uuid}", response_model=SprintDetail)
async def detail_route(
    sprint_uuid: UUID,
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
) -> SprintDetail:
    async with org_scoped_session(ctx.org_id) as db:
        sp = await get_sprint(db, sprint_uuid)
        if sp.org_id != ctx.org_id:
            # Defense-in-depth — RLS would already prevent this.
            raise NotFound(f"Sprint {sprint_uuid} not found")
        ticket_count = await count_tickets_for_sprint(
            db, org_uuid=ctx.org_id, sprint_uuid=sprint_uuid
        )
    return SprintDetail(
        id=sp.id,
        system=sp.system,
        external_id=sp.external_id,
        name=sp.name,
        state=sp.state,
        started_at=sp.started_at,
        ended_at=sp.ended_at,
        completed_at=sp.completed_at,
        board_id=sp.board_id,
        ticket_count=ticket_count,
        # Cost + session aggregates land when Worker joins sessions →
        # sprints; placeholder zeroes for now.
        total_cost_usd=Decimal("0.00"),
        total_sessions=0,
    )
