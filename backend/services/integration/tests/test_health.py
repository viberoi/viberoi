"""Health and readiness endpoint tests."""

import pytest
from fastapi.testclient import TestClient


def test_healthz_returns_ok(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.integration
def test_readyz_returns_ok(client: TestClient) -> None:
    """Requires Postgres + Redis: /readyz pings both."""
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_request_id_header_echoed(client: TestClient) -> None:
    r = client.get("/healthz")
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) > 0
