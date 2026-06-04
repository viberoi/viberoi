"""Tests for the notification-channel CRUD routes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from api.app.auth import ApiAuthContext
from api.routes import notification_channels as nc_routes


@pytest.fixture
def _stub_db(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(nc_routes, "org_scoped_session", lambda _: _Ctx())


def test_list_returns_summaries_without_webhook(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    row = MagicMock()
    row.id = uuid4()
    row.channel = "slack"
    row.webhook_url_ciphertext = b"\x00\x01\x02"
    row.enabled = True
    row.created_at = datetime.now(tz=UTC)
    row.updated_at = datetime.now(tz=UTC)

    # The route calls db.execute(...) → .scalars().all() — stub the chain.
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [row]

    class _DB:
        execute = AsyncMock(return_value=fake_result)

    class _Ctx:
        async def __aenter__(self):
            return _DB()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(nc_routes, "org_scoped_session", lambda _: _Ctx())

    r = client_as(org_admin_ctx).get("/notifications/channels")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["channel"] == "slack"
    assert item["has_webhook_url"] is True
    # Crucially, no decrypted URL anywhere.
    assert "webhook_url" not in item


def test_list_developer_forbidden(
    client_as: Callable,
    developer_ctx: ApiAuthContext,
    _stub_db,
) -> None:
    r = client_as(developer_ctx).get("/notifications/channels")
    assert r.status_code == 403


def test_upsert_orgadmin_succeeds(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = MagicMock()
    row.id = uuid4()
    row.channel = "slack"
    row.webhook_url_ciphertext = b"\x00"
    row.enabled = True
    row.created_at = datetime.now(tz=UTC)
    row.updated_at = datetime.now(tz=UTC)

    fake_result = MagicMock()
    fake_result.scalar_one.return_value = row

    class _DB:
        execute = AsyncMock(return_value=fake_result)

    class _Ctx:
        async def __aenter__(self):
            return _DB()

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(nc_routes, "org_scoped_session", lambda _: _Ctx())
    monkeypatch.setattr(
        nc_routes, "upsert_channel", AsyncMock(return_value=row.id)
    )
    # Bypass the live DNS-resolving SSRF guard.
    monkeypatch.setattr(nc_routes, "assert_safe_slack_webhook_url", lambda _: None)

    r = client_as(org_admin_ctx).post(
        "/notifications/channels",
        json={
            "channel": "slack",
            "webhook_url": "https://hooks.slack.com/services/T/B/X",
        },
    )
    assert r.status_code == 201
    assert r.json()["channel"] == "slack"


def test_upsert_unsafe_url_returns_422(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    def _raise(_: str) -> None:
        raise ValueError("not a slack host")

    monkeypatch.setattr(nc_routes, "assert_safe_slack_webhook_url", _raise)
    r = client_as(org_admin_ctx).post(
        "/notifications/channels",
        json={"channel": "slack", "webhook_url": "https://evil.com/x"},
    )
    assert r.status_code == 422


def test_upsert_developer_forbidden(
    client_as: Callable,
    developer_ctx: ApiAuthContext,
    _stub_db,
) -> None:
    r = client_as(developer_ctx).post(
        "/notifications/channels",
        json={
            "channel": "slack",
            "webhook_url": "https://hooks.slack.com/services/T/B/X",
        },
    )
    assert r.status_code == 403


def test_disable_orgadmin_succeeds(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    monkeypatch.setattr(
        nc_routes, "disable_channel", AsyncMock(return_value=True)
    )
    r = client_as(org_admin_ctx).delete("/notifications/channels/slack")
    assert r.status_code == 204


def test_disable_unknown_channel_returns_404(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    _stub_db,
) -> None:
    r = client_as(org_admin_ctx).delete("/notifications/channels/teams")
    assert r.status_code == 404


def test_disable_when_none_configured_returns_404(
    client_as: Callable,
    org_admin_ctx: ApiAuthContext,
    monkeypatch: pytest.MonkeyPatch,
    _stub_db,
) -> None:
    monkeypatch.setattr(
        nc_routes, "disable_channel", AsyncMock(return_value=False)
    )
    r = client_as(org_admin_ctx).delete("/notifications/channels/slack")
    assert r.status_code == 404
