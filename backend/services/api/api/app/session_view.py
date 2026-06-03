"""Translate SessionRow → response Pydantic.

Pulled out of the route so it's testable in isolation and the route
stays HTTP-shape only.
"""

from __future__ import annotations

from api.schema.responses import SessionDetail, SessionSummary
from viberoi_shared.sessions import SessionRow


def _to_summary_dict(row: SessionRow) -> dict:
    duration: int | None = None
    if row.ended_at is not None and row.started_at is not None:
        duration = int((row.ended_at - row.started_at).total_seconds())
    return {
        "id": row.id,
        "external_id": row.session_id,
        "developer_id": row.developer_id,
        "tool_name": row.tool_name,
        "model": row.tool_model,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "duration_seconds": duration,
        "total_tokens": row.tokens_input + row.tokens_output,
        "cost_usd": row.total_cost_usd,
        "ticket_external_id": row.attr_ticket_id,
        # `attr_sprint_id` is the EXTERNAL sprint id (e.g. Jira sprint
        # number); we keep it as the string the agent saw, not the local
        # sprint UUID, until the Worker is enhanced to join sprints.
        "sprint_id": None,
        "branch_name": row.repo_branch,
        "schema_version": row.schema_version,
    }


def to_summary(row: SessionRow) -> SessionSummary:
    return SessionSummary.model_validate(_to_summary_dict(row))


def to_detail(row: SessionRow) -> SessionDetail:
    base = _to_summary_dict(row)
    base["files_touched_count"] = row.files_touched_count
    base["attribution_signals"] = list(row.attr_signals or [])
    return SessionDetail.model_validate(base)
