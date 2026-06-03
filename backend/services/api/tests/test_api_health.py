"""Health probe tests for the API service."""

from __future__ import annotations

import pytest


def test_healthz_returns_ok(client) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.integration
def test_readyz_reaches_postgres_and_redis(client) -> None:
    """Hits real Postgres + Redis from docker-compose."""
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
