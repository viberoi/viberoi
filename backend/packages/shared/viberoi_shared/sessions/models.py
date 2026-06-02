"""ORM model for the sessions table.

Mirrors `backend/migrations/versions/0001_initial_schema.py`. The
wire-format Pydantic `Session` (in `viberoi_shared.types.session`) is the
API contract; this `SessionRow` is the persistence form. The repository
functions in `viberoi_shared.sessions.repository` convert between them.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, NUMERIC, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from viberoi_shared.db.base import Base


class SessionRow(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("org_id", "session_id", name="uq_sessions_org_session"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    developer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Tool
    tool_name: Mapped[str] = mapped_column(Text, nullable=False)
    tool_surface: Mapped[str] = mapped_column(Text, nullable=False)
    tool_version: Mapped[str] = mapped_column(Text, nullable=False)
    tool_model: Mapped[str] = mapped_column(Text, nullable=False)
    tool_capture_mode: Mapped[str] = mapped_column(Text, nullable=False)
    tool_pricing_type: Mapped[str] = mapped_column(Text, nullable=False)
    tool_pricing_unit: Mapped[str] = mapped_column(Text, nullable=False)
    tool_pricing_rate_usd: Mapped[Decimal] = mapped_column(NUMERIC(20, 12), nullable=False)

    # Timing
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    active_duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    first_commit_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    time_to_first_commit_min: Mapped[int | None] = mapped_column(Integer)

    # Tokens
    tokens_input: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tokens_output: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tokens_cache_read: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    tokens_cache_write: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    total_cost_usd: Mapped[Decimal] = mapped_column(NUMERIC(20, 8), nullable=False)
    is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reconciled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Activity
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    is_agentic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    subagent_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    files_touched: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    files_touched_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    # Code output
    lines_added: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    lines_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    lines_accepted: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    lines_reverted: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_committed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    commit_hashes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    uncommitted_at_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    # Repository
    repo_name: Mapped[str] = mapped_column(Text, nullable=False)
    repo_origin_cwd: Mapped[str] = mapped_column(Text, nullable=False)
    repo_branch: Mapped[str] = mapped_column(Text, nullable=False)
    repo_raw_branch: Mapped[str | None] = mapped_column(Text)
    repo_is_worktree: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    # Attribution
    attr_ticket_id: Mapped[str | None] = mapped_column(Text)
    attr_epic_id: Mapped[str | None] = mapped_column(Text)
    attr_sprint_id: Mapped[str | None] = mapped_column(Text)
    attr_confidence: Mapped[Decimal] = mapped_column(
        NUMERIC(4, 3), nullable=False, server_default="0"
    )
    attr_signals: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    attr_method: Mapped[str] = mapped_column(Text, nullable=False, server_default="branch_parse")

    # Quality
    quality_session_restarts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    quality_file_oscillations: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    quality_token_spike_detected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    quality_no_commit_duration_min: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    quality_is_refunded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    quality_hallucination_risk: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="none"
    )

    # Meta
    captured_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    agent_version: Mapped[str] = mapped_column(Text, nullable=False)
    data_sources: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)

    # Bookkeeping
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
