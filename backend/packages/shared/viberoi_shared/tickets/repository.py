"""CRUD for tickets and sprints.

Integration service writes (upsert on every webhook + periodic sync).
Worker reads for attribution Signals 2/3/4. API reads for sprint detail
and ticket detail screens.

Upserts are keyed on `(org_id, system, external_id)` — the natural
identity from the external system. The same JIRA-142 can appear in
multiple orgs (different tenants); never globally unique.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from viberoi_shared.errors.types import NotFound
from viberoi_shared.tickets.models import Sprint, Ticket


# ── Sprints ────────────────────────────────────────────────────────────────


async def upsert_sprint(
    db: AsyncSession,
    *,
    org_id: UUID,
    system: str,
    external_id: str,
    name: str,
    state: str = "future",
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    completed_at: datetime | None = None,
    board_id: str | None = None,
) -> UUID:
    """Insert or update a sprint by `(org_id, system, external_id)`. Returns row id."""
    values: dict[str, Any] = {
        "org_id": org_id,
        "system": system,
        "external_id": external_id,
        "name": name,
        "state": state,
        "started_at": started_at,
        "ended_at": ended_at,
        "completed_at": completed_at,
        "board_id": board_id,
    }
    stmt = insert(Sprint).values(values)
    update_cols = {
        col: stmt.excluded[col]
        for col in values
        if col not in {"org_id", "system", "external_id"}
    }
    stmt = stmt.on_conflict_do_update(
        constraint="uq_sprints_org_system_external", set_=update_cols
    ).returning(Sprint.id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_sprint_by_external(
    db: AsyncSession, *, org_id: UUID, system: str, external_id: str
) -> Sprint | None:
    stmt = select(Sprint).where(
        Sprint.org_id == org_id,
        Sprint.system == system,
        Sprint.external_id == external_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_sprint(db: AsyncSession, sprint_uuid: UUID) -> Sprint:
    row = await db.get(Sprint, sprint_uuid)
    if row is None:
        raise NotFound(f"Sprint {sprint_uuid} not found")
    return row


async def list_active_sprints(db: AsyncSession, org_uuid: UUID) -> list[Sprint]:
    stmt = (
        select(Sprint)
        .where(Sprint.org_id == org_uuid, Sprint.state == "active")
        .order_by(Sprint.started_at.desc().nullslast())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Tickets ────────────────────────────────────────────────────────────────


async def upsert_ticket(
    db: AsyncSession,
    *,
    org_id: UUID,
    system: str,
    external_id: str,
    title: str,
    status: str,
    created_at_external: datetime,
    closed_at_external: datetime | None = None,
    assignee_developer_id: UUID | None = None,
    epic_external_id: str | None = None,
    sprint_id: UUID | None = None,
    story_points: Decimal | None = None,
    priority: str | None = None,
    pr_file_paths: list[str] | None = None,
) -> UUID:
    """Insert or update a ticket by `(org_id, system, external_id)`. Returns row id."""
    values: dict[str, Any] = {
        "org_id": org_id,
        "system": system,
        "external_id": external_id,
        "title": title,
        "status": status,
        "assignee_developer_id": assignee_developer_id,
        "epic_external_id": epic_external_id,
        "sprint_id": sprint_id,
        "story_points": story_points,
        "priority": priority,
        "created_at_external": created_at_external,
        "closed_at_external": closed_at_external,
        "pr_file_paths": pr_file_paths or [],
    }
    stmt = insert(Ticket).values(values)
    # Identity + created_at_external are immutable; everything else can drift
    # as the ticket evolves in the source system.
    update_cols = {
        col: stmt.excluded[col]
        for col in values
        if col not in {"org_id", "system", "external_id", "created_at_external"}
    }
    stmt = stmt.on_conflict_do_update(
        constraint="uq_tickets_org_system_external", set_=update_cols
    ).returning(Ticket.id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_ticket_by_external(
    db: AsyncSession, *, org_id: UUID, system: str, external_id: str
) -> Ticket | None:
    stmt = select(Ticket).where(
        Ticket.org_id == org_id,
        Ticket.system == system,
        Ticket.external_id == external_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_ticket(db: AsyncSession, ticket_uuid: UUID) -> Ticket:
    row = await db.get(Ticket, ticket_uuid)
    if row is None:
        raise NotFound(f"Ticket {ticket_uuid} not found")
    return row


async def list_tickets_for_sprint(
    db: AsyncSession, *, org_uuid: UUID, sprint_uuid: UUID
) -> list[Ticket]:
    stmt = (
        select(Ticket)
        .where(Ticket.org_id == org_uuid, Ticket.sprint_id == sprint_uuid)
        .order_by(Ticket.external_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def find_tickets_by_external_ids(
    db: AsyncSession, *, org_uuid: UUID, external_ids: list[str]
) -> list[Ticket]:
    """Bulk lookup — used by the Worker when an S3 batch references many tickets."""
    if not external_ids:
        return []
    stmt = select(Ticket).where(
        Ticket.org_id == org_uuid, Ticket.external_id.in_(external_ids)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
