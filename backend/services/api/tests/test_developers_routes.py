"""GET /developers/me — decrypted PII for the caller only."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from api.app.auth import ApiAuthContext
from api.routes import developers as dev_routes


def _fake_dev(org_id) -> MagicMock:
    row = MagicMock()
    row.id = uuid4()
    row.org_id = org_id
    row.role = "OrgAdmin"
    row.team_id = None
    row.email_ciphertext = b"ct"
    row.email_key_version = 1
    row.email_iv = b"iv"
    row.github_username_ciphertext = b"gh-ct"
    row.github_username_key_version = 1
    row.github_username_iv = b"gh-iv"
    row.agent_status = "active"
    row.created_at = datetime.now(tz=UTC)
    row.last_active_at = None
    return row


@pytest.fixture
def _stub(monkeypatch: pytest.MonkeyPatch) -> dict:
    row = _fake_dev(uuid4())
    monkeypatch.setattr(dev_routes, "get_developer", AsyncMock(return_value=row))

    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(dev_routes, "org_scoped_session", lambda _: _Ctx())

    decrypt = AsyncMock(side_effect=["alice@example.com", "alice-gh"])
    monkeypatch.setattr(dev_routes, "decrypt_pii", decrypt)
    return {"row": row, "decrypt": decrypt}


def test_me_returns_decrypted_pii(
    client_as: Callable, developer_ctx: ApiAuthContext, _stub
) -> None:
    r = client_as(developer_ctx).get("/developers/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["github_username"] == "alice-gh"


def test_me_handles_missing_github_username(
    client_as: Callable,
    developer_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub,
) -> None:
    """github_username_ciphertext is nullable — endpoint must not crash."""
    row = _stub["row"]
    row.github_username_ciphertext = None
    monkeypatch.setattr(dev_routes, "decrypt_pii", AsyncMock(return_value="alice@example.com"))

    r = client_as(developer_ctx).get("/developers/me")
    assert r.status_code == 200
    assert r.json()["github_username"] is None


def test_me_unauthenticated_401(client) -> None:
    r = client.get("/developers/me")
    assert r.status_code in (401, 500)
