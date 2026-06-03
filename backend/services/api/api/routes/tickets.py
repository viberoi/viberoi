"""Ticket detail — single row by id, with placeholder rollups."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from api.app.auth import ApiAuthContext, require_role
from api.schema.responses import TicketDetail
from viberoi_shared.db import org_scoped_session
from viberoi_shared.errors import NotFound
from viberoi_shared.logging import get_logger
from viberoi_shared.tickets import get_ticket
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()


@router.get("/{ticket_uuid}", response_model=TicketDetail)
async def detail_route(
    ticket_uuid: UUID,
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
) -> TicketDetail:
    async with org_scoped_session(ctx.org_id) as db:
        t = await get_ticket(db, ticket_uuid)
        if t.org_id != ctx.org_id:
            raise NotFound(f"Ticket {ticket_uuid} not found")
    return TicketDetail(
        id=t.id,
        system=t.system,
        external_id=t.external_id,
        title=t.title,
        status=t.status,
        sprint_id=t.sprint_id,
        assignee_developer_id=t.assignee_developer_id,
        story_points=t.story_points,
        priority=t.priority,
        created_at_external=t.created_at_external,
        closed_at_external=t.closed_at_external,
        # Aggregates require a join through sessions.attr_ticket_id;
        # placeholder until Slice 5C.
        total_sessions=0,
        total_cost_usd=Decimal("0.00"),
    )
