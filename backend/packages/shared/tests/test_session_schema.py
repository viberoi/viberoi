"""Validate the locked v1.0 session schema against a realistic payload."""

import pytest
from pydantic import ValidationError

from viberoi_shared.types import (
    SCHEMA_VERSION,
    Session,
)
from viberoi_shared.types.enums import SessionMode, Tool


def _fixture_payload() -> dict:
    return {
        "session_id": "local_d7f613d2-dd58-4cc5-9238-a819ae844f4b",
        "developer_id": "dev_adnan_123",
        "org_id": "org_rapyder_456",
        "tool": {
            "name": "claude-code",
            "surface": "desktop_app",
            "version": "2.1.128",
            "model": "claude-sonnet-4-6",
            "capture_mode": "local_exact",
            "pricing_model": {
                "type": "subscription",
                "unit": "tokens",
                "rate_usd": 0.000003,
            },
        },
        "timing": {
            "started_at": "2026-05-06T09:28:35Z",
            "ended_at": "2026-05-06T10:42:55Z",
            "active_duration_min": 74,
            "first_commit_at": "2026-05-06T10:55:00Z",
            "time_to_first_commit_min": 86,
        },
        "tokens": {
            "input": 3,
            "output": 226,
            "cache_read": 163906,
            "cache_write": 188,
            "total_cost_usd": 0.0042,
            "is_estimated": False,
            "reconciled": False,
            "reconciled_at": None,
        },
        "activity": {
            "turn_count": 4,
            "mode": "agent",
            "is_agentic": True,
            "subagent_count": 4,
            "files_touched": ["src/payments/gateway.ts", ".husky/pre-commit"],
            "files_touched_count": 2,
        },
        "code_output": {
            "lines_added": 47,
            "lines_deleted": 12,
            "lines_accepted": 38,
            "lines_reverted": 9,
            "is_committed": True,
            "commit_hashes": ["7adc7be", "ce34db2"],
            "uncommitted_at_end": False,
        },
        "repository": {
            "name": "wvp-backend",
            "origin_cwd": "C:/Users/AdnanKhan/wvp-backend",
            "branch": "feature/JIRA-142-payment-gateway",
            "raw_branch": "claude/xenodochial-joliot-361764",
            "is_worktree": True,
        },
        "attribution": {
            "ticket_id": "JIRA-142",
            "epic_id": "EPIC-12",
            "sprint_id": "SPRINT-42",
            "confidence": 0.87,
            "signals": ["branch_match", "file_overlap", "temporal_proximity"],
            "method": "branch_parse",
        },
        "quality": {
            "session_restarts": 0,
            "file_oscillations": 1,
            "token_spike_detected": False,
            "no_commit_duration_min": 0,
            "is_refunded": False,
            "hallucination_risk": "none",
        },
        "meta": {
            "captured_at": "2026-05-06T10:43:00Z",
            "agent_version": "0.1.0",
            "data_sources": ["local_jsonl", "git_diff", "worktree_map"],
            "schema_version": "1.0",
        },
    }


def test_session_round_trip():
    payload = _fixture_payload()
    s = Session.model_validate(payload)
    assert s.session_id == payload["session_id"]
    assert s.tool.name is Tool.CLAUDE_CODE
    assert s.activity.mode is SessionMode.AGENT
    assert s.attribution.confidence == 0.87
    assert s.meta.schema_version == SCHEMA_VERSION
    dumped = s.model_dump(mode="json")
    again = Session.model_validate(dumped)
    assert again == s


def test_session_rejects_unknown_field():
    payload = _fixture_payload()
    payload["new_field"] = "rejected"
    with pytest.raises(ValidationError):
        Session.model_validate(payload)


def test_session_rejects_negative_tokens():
    payload = _fixture_payload()
    payload["tokens"]["input"] = -1
    with pytest.raises(ValidationError):
        Session.model_validate(payload)


def test_session_rejects_confidence_out_of_range():
    payload = _fixture_payload()
    payload["attribution"]["confidence"] = 1.5
    with pytest.raises(ValidationError):
        Session.model_validate(payload)


def test_session_minimal_attribution():
    payload = _fixture_payload()
    payload["attribution"]["ticket_id"] = None
    payload["attribution"]["epic_id"] = None
    payload["attribution"]["sprint_id"] = None
    payload["timing"]["first_commit_at"] = None
    payload["timing"]["time_to_first_commit_min"] = None
    s = Session.model_validate(payload)
    assert s.attribution.ticket_id is None
    assert s.timing.first_commit_at is None
