"""Sessions list + detail.

  GET /sessions             — paginated, role-scoped
  GET /sessions/{id}        — single session, role-scoped
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.app.auth import ApiAuthContext, require_role
from api.app.session_view import to_detail, to_summary
from api.schema.responses import SessionDetail, SessionListResponse
from viberoi_shared.db import org_scoped_session
from viberoi_shared.errors import NotFound
from viberoi_shared.logging import get_logger
from viberoi_shared.orgs import get_developer
from viberoi_shared.sessions import (
    SESSION_LIST_DEFAULT,
    SESSION_LIST_HARD_CAP,
    get_by_id,
    list_sessions,
)
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=SessionListResponse)
async def list_route(
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
    cursor: str | None = Query(default=None, min_length=1, max_length=512),
    limit: int = Query(
        default=SESSION_LIST_DEFAULT, ge=1, le=SESSION_LIST_HARD_CAP
    ),
) -> SessionListResponse:
    async with org_scoped_session(ctx.org_id) as db:
        rows, next_cursor = await list_sessions(
            db,
            org_uuid=ctx.org_id,
            viewer_role=ctx.role,
            viewer_developer_id=ctx.developer_id,
            viewer_team_id=ctx.team_id,
            cursor=cursor,
            limit=limit,
        )
    return SessionListResponse(
        items=[to_summary(r) for r in rows], next_cursor=next_cursor
    )


@router.get("/{session_uuid}", response_model=SessionDetail)
async def detail_route(
    session_uuid: UUID,
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
) -> SessionDetail:
    async with org_scoped_session(ctx.org_id) as db:
        row = await get_by_id(db, session_uuid)

    # Defense-in-depth — RLS would already block a cross-org row, but
    # mirror what /sprints and /tickets do explicitly so the guard
    # doesn't disappear under a future RLS regression.
    if row.org_id != ctx.org_id:
        raise NotFound(f"Session {session_uuid} not found")

    # Role-based visibility within the org.
    if ctx.role == Role.DEVELOPER and row.developer_id != ctx.developer_id:
        raise NotFound(f"Session {session_uuid} not found")
    if ctx.role == Role.TEAM_LEAD:
        # An unassigned TeamLead (no team_id) sees nothing — match the
        # list endpoint, which short-circuits to empty in the same state.
        # Otherwise both ctx and the session's developer must share a team.
        if ctx.team_id is None:
            raise NotFound(f"Session {session_uuid} not found")
        async with org_scoped_session(ctx.org_id) as db:
            dev = await get_developer(db, row.developer_id)
        if dev.team_id != ctx.team_id:
            raise NotFound(f"Session {session_uuid} not found")

    return to_detail(row)
