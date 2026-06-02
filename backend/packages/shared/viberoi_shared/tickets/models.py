"""ORM models for tickets and sprints.

Mirrors migration `0004_tickets_sprints_oauth.py`. Populated by the
Integration service (Jira / Linear / GitHub Issues). Read by the Worker
for attribution Signals 2/3/4 and by the API for sprint/ticket views.

`Ticket.title` IS stored — per spec § privacy, ticket TITLES are OK for
attribution Signal 5, but PR/issue bodies are NOT.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, NUMERIC, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from viberoi_shared.db.base import Base


class Sprint(Base):
    __tablename__ = "sprints"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "system", "external_id", name="uq_sprints_org_system_external"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
    )
    system: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default="future")
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    board_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "system", "external_id", name="uq_tickets_org_system_external"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
    )
    system: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    assignee_developer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="SET NULL"),
    )
    epic_external_id: Mapped[str | None] = mapped_column(Text)
    sprint_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sprints.id", ondelete="SET NULL"),
    )
    story_points: Mapped[Decimal | None] = mapped_column(NUMERIC(8, 2))
    priority: Mapped[str | None] = mapped_column(Text)
    created_at_external: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    closed_at_external: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    pr_file_paths: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
