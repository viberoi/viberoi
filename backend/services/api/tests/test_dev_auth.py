"""Tests for the `env=dev` X-Dev-* auth passthrough.

These tests use a fresh app per-test (no dependency override) so the
real `authenticate` dep runs end-to-end.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.routes import sessions as sessions_routes
from viberoi_shared.config import Env, get_settings


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force env=dev for this module + clear the lru_cache."""
    get_settings.cache_clear()
    monkeypatch.setenv("VIBEROI_ENV", "dev")


@pytest.fixture
def fresh_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Real authenticate dep + sessions route stubbed at the repository
    layer so we never actually hit the DB."""
    rows = []
    monkeypatch.setattr(
        sessions_routes,
        "list_sessions",
        AsyncMock(return_value=(rows, None)),
    )

    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(sessions_routes, "org_scoped_session", lambda _: _Ctx())
    return TestClient(create_app(), raise_server_exceptions=False)


def test_dev_headers_authenticate_request(fresh_client: TestClient) -> None:
    r = fresh_client.get(
        "/sessions",
        headers={
            "X-Dev-Developer-Id": str(uuid4()),
            "X-Dev-Org-Id": str(uuid4()),
            "X-Dev-Role": "OrgAdmin",
        },
    )
    assert r.status_code == 200


def test_dev_headers_with_team_id_routes_team_lead(
    fresh_client: TestClient,
) -> None:
    r = fresh_client.get(
        "/sessions",
        headers={
            "X-Dev-Developer-Id": str(uuid4()),
            "X-Dev-Org-Id": str(uuid4()),
            "X-Dev-Role": "TeamLead",
            "X-Dev-Team-Id": str(uuid4()),
        },
    )
    assert r.status_code == 200


def test_dev_headers_with_bad_uuid_rejected(fresh_client: TestClient) -> None:
    """Malformed dev header → falls through to JWT path → 401."""
    r = fresh_client.get(
        "/sessions",
        headers={
            "X-Dev-Developer-Id": "not-a-uuid",
            "X-Dev-Org-Id": str(uuid4()),
            "X-Dev-Role": "OrgAdmin",
        },
    )
    assert r.status_code in (401, 500)


def test_dev_headers_with_invalid_role_rejected(fresh_client: TestClient) -> None:
    r = fresh_client.get(
        "/sessions",
        headers={
            "X-Dev-Developer-Id": str(uuid4()),
            "X-Dev-Org-Id": str(uuid4()),
            "X-Dev-Role": "GodMode",
        },
    )
    assert r.status_code in (401, 500)


def test_dev_headers_ignored_outside_dev_env(
    monkeypatch: pytest.MonkeyPatch, fresh_client: TestClient
) -> None:
    """Same headers but env=prod → JWT path runs and fails."""
    monkeypatch.setenv("VIBEROI_ENV", "prod")
    get_settings.cache_clear()
    r = fresh_client.get(
        "/sessions",
        headers={
            "X-Dev-Developer-Id": str(uuid4()),
            "X-Dev-Org-Id": str(uuid4()),
            "X-Dev-Role": "OrgAdmin",
        },
    )
    assert r.status_code in (401, 500)
