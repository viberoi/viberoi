"""Pydantic response models for the API service.

Every model freezes its shape with `extra="forbid"` so a stray field
addition doesn't silently leak through the OpenAPI schema.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


# ── Sessions ────────────────────────────────────────────────────────────────


class SessionSummary(BaseModel):
    """One row in the `GET /sessions` paginated list."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    external_id: str
    developer_id: UUID
    tool_name: str
    model: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    total_tokens: int
    cost_usd: Decimal
    ticket_external_id: str | None
    sprint_id: UUID | None
    branch_name: str | None
    schema_version: str


class SessionListResponse(BaseModel):
    """`GET /sessions` envelope."""

    model_config = ConfigDict(extra="forbid")

    items: list[SessionSummary]
    next_cursor: str | None


class SessionDetail(SessionSummary):
    """`GET /sessions/{id}` — summary + everything else the dashboard renders.

    Stays metadata-only per the privacy rule: file PATHS are OK, file
    contents are not. Token counts + cost are numbers. No prompts, no
    completions, no commit-message bodies.
    """

    model_config = ConfigDict(extra="forbid")

    # Token breakdown
    tokens_input: int
    tokens_output: int
    tokens_cache_read: int
    tokens_cache_write: int
    is_estimated: bool

    # Activity
    turn_count: int
    subagent_count: int
    mode: str
    is_agentic: bool

    # Code output (numbers only, no diffs)
    lines_added: int
    lines_deleted: int
    is_committed: bool
    commit_count: int

    # Quality signals (deferred fields default to None; populated when
    # Worker has the per-turn token series)
    session_restarts: int | None
    file_oscillations: int | None

    # Attribution
    attribution_signals: list[str]
    attribution_confidence: float | None
    attribution_method: str | None

    # Files touched (PATHS only — privacy-safe)
    files_touched_count: int
    files_touched: list[str]

    # Repo context
    repo_name: str | None
    repo_cwd: str | None


# ── Sprints ────────────────────────────────────────────────────────────────


class SprintSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    system: str
    external_id: str
    name: str
    state: str
    started_at: datetime | None
    ended_at: datetime | None
    completed_at: datetime | None
    board_id: str | None
    ticket_count: int


class SprintListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SprintSummary]


class SprintDetail(SprintSummary):
    model_config = ConfigDict(extra="forbid")

    total_cost_usd: Decimal
    total_sessions: int


# ── Tickets ─────────────────────────────────────────────────────────────────


class TicketDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    system: str
    external_id: str
    title: str
    status: str
    sprint_id: UUID | None
    assignee_developer_id: UUID | None
    story_points: Decimal | None
    priority: str | None
    created_at_external: datetime
    closed_at_external: datetime | None
    total_sessions: int
    total_cost_usd: Decimal


class TicketListResponse(BaseModel):
    """`GET /sprints/{id}/tickets` envelope."""

    model_config = ConfigDict(extra="forbid")

    items: list[TicketDetail]


# ── Notification channels ──────────────────────────────────────────────────


class NotificationChannelSummary(BaseModel):
    """One row in `GET /notifications/channels`.

    Never includes the decrypted webhook URL — we only expose `has_url`
    (boolean) + the channel's metadata so the UI can show a "configured"
    badge without leaking the URL back to the browser.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID
    channel: str
    has_webhook_url: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime


class NotificationChannelListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NotificationChannelSummary]


# ── KPIs ────────────────────────────────────────────────────────────────────


class KpiSnapshot(BaseModel):
    """Org-level rollup. Window = last 30 days unless overridden."""

    model_config = ConfigDict(extra="forbid")

    window_days: int
    total_sessions: int
    total_tokens: int
    total_cost_usd: Decimal
    active_developers: int
    avg_session_duration_seconds: int | None
    hallucination_loop_rate: float | None


# ── Developers ──────────────────────────────────────────────────────────────


class DeveloperProfile(BaseModel):
    """`GET /developers/me` — caller's own row, decrypted PII included.

    PII (email, github_username) is decrypted server-side and returned
    only to the row's own owner. We never return decrypted PII for
    another developer.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID
    org_id: UUID
    role: str
    team_id: UUID | None
    email: str
    github_username: str | None
    agent_status: str
    created_at: datetime
    last_active_at: datetime | None
