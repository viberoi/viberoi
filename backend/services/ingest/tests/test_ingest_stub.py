"""Smoke tests for the Slice 1 ingest stubs.

Proves the service can accept a valid Session payload (locked v1.0
schema) and that the shared library types integrate correctly.
"""

from fastapi.testclient import TestClient


def _valid_session_payload() -> dict:
    return {
        "session": {
            "session_id": "local_test-1234",
            "developer_id": "dev_test",
            "org_id": "org_test",
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
                "first_commit_at": None,
                "time_to_first_commit_min": None,
            },
            "tokens": {
                "input": 3,
                "output": 226,
                "cache_read": 0,
                "cache_write": 0,
                "total_cost_usd": 0.0042,
                "is_estimated": False,
                "reconciled": False,
                "reconciled_at": None,
            },
            "activity": {
                "turn_count": 4,
                "mode": "agent",
                "is_agentic": True,
                "subagent_count": 0,
                "files_touched": [],
                "files_touched_count": 0,
            },
            "code_output": {
                "lines_added": 0,
                "lines_deleted": 0,
                "lines_accepted": 0,
                "lines_reverted": 0,
                "is_committed": False,
                "commit_hashes": [],
                "uncommitted_at_end": True,
            },
            "repository": {
                "name": "test-repo",
                "origin_cwd": "/tmp/test-repo",
                "branch": "main",
                "raw_branch": None,
                "is_worktree": False,
            },
            "attribution": {
                "ticket_id": None,
                "epic_id": None,
                "sprint_id": None,
                "confidence": 0.0,
                "signals": [],
                "method": "branch_parse",
            },
            "quality": {
                "session_restarts": 0,
                "file_oscillations": 0,
                "token_spike_detected": False,
                "no_commit_duration_min": 0,
                "is_refunded": False,
                "hallucination_risk": "none",
            },
            "meta": {
                "captured_at": "2026-05-06T10:43:00Z",
                "agent_version": "0.1.0",
                "data_sources": ["local_jsonl"],
                "schema_version": "1.0",
            },
        },
    }


def test_ingest_session_accepts_valid_payload(client: TestClient) -> None:
    r = client.post("/ingest/session", json=_valid_session_payload())
    assert r.status_code == 202
    body = r.json()
    assert body["accepted"] == 1
    assert body["rejected"] == 0


def test_ingest_session_rejects_missing_required_field(client: TestClient) -> None:
    bad = _valid_session_payload()
    del bad["session"]["tool"]
    r = client.post("/ingest/session", json=bad)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_failed"


def test_ingest_batch_accepts_multiple(client: TestClient) -> None:
    batch = [_valid_session_payload(), _valid_session_payload()]
    r = client.post("/ingest/sessions", json=batch)
    assert r.status_code == 202
    assert r.json()["accepted"] == 2


def test_ingest_batch_rejects_over_limit(client: TestClient) -> None:
    batch = [_valid_session_payload()] * 101
    r = client.post("/ingest/sessions", json=batch)
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_failed"
    assert body["error"]["details"]["batch_size"] == 101
