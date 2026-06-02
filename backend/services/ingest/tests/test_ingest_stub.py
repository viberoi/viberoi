"""Ingest service tests — unit-level, no LocalStack required.

Auth is mocked via FastAPI dependency_overrides so we exercise the
endpoint logic (validation, org_id matching, batch limits, error shape)
without booting a real DB. Integration tests that exercise the real auth
+ S3 path live in `tests/test_ingest_e2e.py` and are marked `integration`.
"""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ingest.app.auth import AuthContext, authenticate


@pytest.fixture
def auth_ctx() -> AuthContext:
    """A fixed AuthContext used by all mocked-auth tests."""
    return AuthContext(developer_id=uuid4(), org_id=uuid4())


@pytest.fixture
def client_with_auth(app: FastAPI, auth_ctx: AuthContext) -> TestClient:
    """TestClient with authenticate() overridden to always succeed."""
    app.dependency_overrides[authenticate] = lambda: auth_ctx
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _session_payload(*, org_id: str, developer_id: str) -> dict:
    return {
        "session_id": "local_test-1234",
        "developer_id": developer_id,
        "org_id": org_id,
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
    }


def test_ingest_rejects_unauthenticated(client: TestClient) -> None:
    """Without the auth override, the real `authenticate` runs and 401s
    on missing headers."""
    payload = _session_payload(org_id=str(uuid4()), developer_id=str(uuid4()))
    r = client.post("/ingest/session", json=payload)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_ingest_rejects_wrong_org_id_in_body(
    client_with_auth: TestClient,
    auth_ctx: AuthContext,
) -> None:
    """Authenticated as org A, body claims org B — Forbidden."""
    other_org = uuid4()
    payload = _session_payload(
        org_id=str(other_org), developer_id=str(auth_ctx.developer_id)
    )
    r = client_with_auth.post("/ingest/session", json=payload)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_ingest_rejects_wrong_developer_id_in_body(
    client_with_auth: TestClient,
    auth_ctx: AuthContext,
) -> None:
    payload = _session_payload(
        org_id=str(auth_ctx.org_id), developer_id=str(uuid4())
    )
    r = client_with_auth.post("/ingest/session", json=payload)
    assert r.status_code == 403


def test_ingest_rejects_missing_required_field(
    client_with_auth: TestClient,
    auth_ctx: AuthContext,
) -> None:
    bad = _session_payload(
        org_id=str(auth_ctx.org_id), developer_id=str(auth_ctx.developer_id)
    )
    del bad["tool"]
    r = client_with_auth.post("/ingest/session", json=bad)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_failed"


def test_ingest_batch_rejects_over_limit(
    client_with_auth: TestClient,
    auth_ctx: AuthContext,
) -> None:
    payload = _session_payload(
        org_id=str(auth_ctx.org_id), developer_id=str(auth_ctx.developer_id)
    )
    batch = [payload] * 101
    r = client_with_auth.post("/ingest/sessions", json=batch)
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_failed"
    assert body["error"]["details"]["batch_size"] == 101


def test_request_id_header_echoed(client: TestClient) -> None:
    """Healthz response must carry X-Request-ID (proves middleware installed)."""
    r = client.get("/healthz")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) > 0


def test_request_id_propagated_when_supplied(client: TestClient) -> None:
    """If the client sends X-Request-ID, the middleware echoes it back."""
    rid = "test-request-id-abc"
    r = client.get("/healthz", headers={"X-Request-ID": rid})
    assert r.headers["X-Request-ID"] == rid
