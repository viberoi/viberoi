"""CRUD functions for the sessions table.

Services pass Pydantic `Session` objects in; the repository handles the
flatten/inflate dance with the ORM `SessionRow`. Services NEVER touch
`SessionRow` directly.

The Ingest service writes via `upsert()` — idempotent on
`(org_id, session_id)` so agent retries are safe. The Worker service
reads and recomputes attribution via `get_by_external_id()` /
`get_by_id()` etc.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from viberoi_shared.errors.types import NotFound, ValidationFailed
from viberoi_shared.orgs.models import Developer
from viberoi_shared.sessions.models import SessionRow
from viberoi_shared.types.enums import Role
from viberoi_shared.types.session import Session

# Columns that NEVER change after first insert. Excluded from upsert
# update_set so the unique identifier and original timestamps stay stable.
_IMMUTABLE_ON_UPDATE = frozenset(
    {"session_id", "developer_id", "org_id", "started_at", "captured_at", "created_at"}
)


def _pydantic_to_columns(
    session: Session, *, developer_uuid: UUID, org_uuid: UUID
) -> dict[str, Any]:
    """Flatten a Pydantic Session into the SessionRow column dict."""
    return {
        "session_id": session.session_id,
        "developer_id": developer_uuid,
        "org_id": org_uuid,
        # Tool
        "tool_name": session.tool.name.value,
        "tool_surface": session.tool.surface.value,
        "tool_version": session.tool.version,
        "tool_model": session.tool.model,
        "tool_capture_mode": session.tool.capture_mode.value,
        "tool_pricing_type": session.tool.pricing_model.type.value,
        "tool_pricing_unit": session.tool.pricing_model.unit.value,
        "tool_pricing_rate_usd": Decimal(str(session.tool.pricing_model.rate_usd)),
        # Timing
        "started_at": session.timing.started_at,
        "ended_at": session.timing.ended_at,
        "active_duration_min": session.timing.active_duration_min,
        "first_commit_at": session.timing.first_commit_at,
        "time_to_first_commit_min": session.timing.time_to_first_commit_min,
        # Tokens
        "tokens_input": session.tokens.input,
        "tokens_output": session.tokens.output,
        "tokens_cache_read": session.tokens.cache_read,
        "tokens_cache_write": session.tokens.cache_write,
        "total_cost_usd": Decimal(str(session.tokens.total_cost_usd)),
        "is_estimated": session.tokens.is_estimated,
        "reconciled": session.tokens.reconciled,
        "reconciled_at": session.tokens.reconciled_at,
        # Activity
        "turn_count": session.activity.turn_count,
        "mode": session.activity.mode.value,
        "is_agentic": session.activity.is_agentic,
        "subagent_count": session.activity.subagent_count,
        "files_touched": session.activity.files_touched,
        "files_touched_count": session.activity.files_touched_count,
        # Code output
        "lines_added": session.code_output.lines_added,
        "lines_deleted": session.code_output.lines_deleted,
        "lines_accepted": session.code_output.lines_accepted,
        "lines_reverted": session.code_output.lines_reverted,
        "is_committed": session.code_output.is_committed,
        "commit_hashes": session.code_output.commit_hashes,
        "uncommitted_at_end": session.code_output.uncommitted_at_end,
        # Repository
        "repo_name": session.repository.name,
        "repo_origin_cwd": session.repository.origin_cwd,
        "repo_branch": session.repository.branch,
        "repo_raw_branch": session.repository.raw_branch,
        "repo_is_worktree": session.repository.is_worktree,
        # Attribution
        "attr_ticket_id": session.attribution.ticket_id,
        "attr_epic_id": session.attribution.epic_id,
        "attr_sprint_id": session.attribution.sprint_id,
        "attr_confidence": Decimal(str(session.attribution.confidence)),
        "attr_signals": session.attribution.signals,
        "attr_method": session.attribution.method.value,
        # Quality
        "quality_session_restarts": session.quality.session_restarts,
        "quality_file_oscillations": session.quality.file_oscillations,
        "quality_token_spike_detected": session.quality.token_spike_detected,
        "quality_no_commit_duration_min": session.quality.no_commit_duration_min,
        "quality_is_refunded": session.quality.is_refunded,
        "quality_hallucination_risk": session.quality.hallucination_risk.value,
        # Meta
        "captured_at": session.meta.captured_at,
        "agent_version": session.meta.agent_version,
        "data_sources": [ds.value for ds in session.meta.data_sources],
        "schema_version": session.meta.schema_version,
    }


async def upsert(
    db: AsyncSession,
    session: Session,
    *,
    developer_uuid: UUID,
    org_uuid: UUID,
) -> UUID:
    """Insert or update a session by `(org_id, session_id)`. Returns row id.

    Idempotent — the agent may retry on network failure; the UNIQUE
    constraint on `(org_id, session_id)` makes duplicate pushes no-ops.
    On conflict, mutable fields (attribution backfill, reconciliation,
    quality re-scoring) are updated; identity fields stay frozen.
    """
    values = _pydantic_to_columns(session, developer_uuid=developer_uuid, org_uuid=org_uuid)
    stmt = insert(SessionRow).values(values)
    update_cols = {
        col: stmt.excluded[col] for col in values if col not in _IMMUTABLE_ON_UPDATE
    }
    stmt = stmt.on_conflict_do_update(
        constraint="uq_sessions_org_session", set_=update_cols
    ).returning(SessionRow.id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_by_id(db: AsyncSession, session_uuid: UUID) -> SessionRow:
    row = await db.get(SessionRow, session_uuid)
    if row is None:
        raise NotFound(f"Session {session_uuid} not found")
    return row


async def get_by_external_id(
    db: AsyncSession, *, org_uuid: UUID, external_session_id: str
) -> SessionRow | None:
    stmt = select(SessionRow).where(
        SessionRow.org_id == org_uuid,
        SessionRow.session_id == external_session_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Paginated list (Slice 5B) ───────────────────────────────────────────────


# Hard upper bound — even an explicit `?limit=999` won't go above this.
SESSION_LIST_HARD_CAP = 200
SESSION_LIST_DEFAULT = 50


def _encode_cursor(started_at: datetime, session_uuid: UUID) -> str:
    """Cursor is base64(`{started_at_iso}|{uuid}`) — opaque to callers."""
    raw = f"{started_at.isoformat()}|{session_uuid}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + padding).decode("utf-8")
        ts_str, uuid_str = raw.split("|", 1)
        return datetime.fromisoformat(ts_str), UUID(uuid_str)
    except (binascii.Error, UnicodeDecodeError, ValueError) as e:
        raise ValidationFailed("Invalid pagination cursor.") from e


async def list_sessions(
    db: AsyncSession,
    *,
    org_uuid: UUID,
    viewer_role: Role,
    viewer_developer_id: UUID,
    viewer_team_id: UUID | None,
    cursor: str | None = None,
    limit: int = SESSION_LIST_DEFAULT,
) -> tuple[list[SessionRow], str | None]:
    """Return one page of sessions plus the next cursor.

    Role-based filtering applied here so callers don't get to choose:
      - OrgAdmin → all org sessions
      - TeamLead → only sessions by developers in the lead's team
      - Developer → only the caller's own sessions

    Ordering: `(started_at DESC, id DESC)` — stable across inserts.
    Cursor encodes the last `(started_at, id)` pair of the page; the
    next request returns rows strictly older than it.
    """
    limit = max(1, min(limit, SESSION_LIST_HARD_CAP))

    stmt = select(SessionRow).where(SessionRow.org_id == org_uuid)

    if viewer_role == Role.DEVELOPER:
        stmt = stmt.where(SessionRow.developer_id == viewer_developer_id)
    elif viewer_role == Role.TEAM_LEAD:
        if viewer_team_id is None:
            # TeamLead with no team assigned → no visible rows.
            return [], None
        stmt = stmt.join(
            Developer, Developer.id == SessionRow.developer_id
        ).where(Developer.team_id == viewer_team_id)
    # OrgAdmin: no additional filter — RLS already scopes to org_id.

    if cursor is not None:
        cur_started, cur_id = _decode_cursor(cursor)
        # Lexicographic comparison on (started_at, id) — equivalent to a
        # composite-key < check, which Postgres can use the index for.
        stmt = stmt.where(
            or_(
                SessionRow.started_at < cur_started,
                and_(
                    SessionRow.started_at == cur_started,
                    SessionRow.id < cur_id,
                ),
            )
        )

    stmt = (
        stmt.order_by(SessionRow.started_at.desc(), SessionRow.id.desc())
        # Fetch limit+1 so we know whether there's another page.
        .limit(limit + 1)
    )

    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = _encode_cursor(last.started_at, last.id)

    return rows, next_cursor
