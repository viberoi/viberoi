"""Unit tests for `integration.app.sync.run_sync`.

Mocks the adapter + the shared persistence calls; no DB/Redis/network.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from integration.app import sync as sync_mod
from integration.app.providers import registry
from integration.app.providers.base import (
    ProviderConnection,
    SyncResult,
    TokenRefreshError,
)

from viberoi_shared.errors import NotFound


@pytest.fixture
def patch_shared(monkeypatch: pytest.MonkeyPatch):
    """Stub out org_scoped_session + the shared repository helpers."""
    fake_db = MagicMock()

    class _Ctx:
        async def __aenter__(self):
            return fake_db

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(sync_mod, "org_scoped_session", lambda _: _Ctx())
    monkeypatch.setattr(sync_mod, "get_token_for_org", AsyncMock())
    monkeypatch.setattr(sync_mod, "store_token", AsyncMock(return_value=uuid4()))
    monkeypatch.setattr(sync_mod, "revoke_token", AsyncMock(return_value=True))
    monkeypatch.setattr(sync_mod, "mark_synced", AsyncMock())
    return sync_mod


def _token_data(*, expires_in_seconds: int | None = 3600) -> dict:
    expires_at: datetime | None
    if expires_in_seconds is None:
        expires_at = None
    else:
        expires_at = datetime.now(tz=UTC) + timedelta(seconds=expires_in_seconds)
    return {
        "id": uuid4(),
        "access_token": "at_test",
        "refresh_token": "rt_test",
        "webhook_secret": "ws_test",
        "expires_at": expires_at,
        "scope": "read",
        "installation_id": None,
        "installed_by_developer_id": uuid4(),
        "discovery_metadata": {"cloud_id": "cid"},
        "last_sync_at": None,
    }


async def test_run_sync_raises_notfound_when_no_token(patch_shared) -> None:
    patch_shared.get_token_for_org.return_value = None
    req = sync_mod.SyncRequest(
        org_id=uuid4(), provider="github", sync_type="manual"
    )
    with pytest.raises(NotFound):
        await sync_mod.run_sync(req)


async def test_run_sync_calls_adapter_and_marks_synced(
    patch_shared, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_shared.get_token_for_org.return_value = _token_data()
    adapter = MagicMock()
    adapter.sync = AsyncMock(
        return_value=SyncResult(tickets_upserted=3, sprints_upserted=1)
    )
    adapter.refresh = AsyncMock()
    registry.reset()
    registry.override_for_test("github", adapter)

    req = sync_mod.SyncRequest(
        org_id=uuid4(), provider="github", sync_type="manual"
    )
    result = await sync_mod.run_sync(req)

    assert result.tickets_upserted == 3
    assert result.sprints_upserted == 1
    adapter.sync.assert_awaited_once()
    adapter.refresh.assert_not_awaited()  # not near expiry
    patch_shared.mark_synced.assert_awaited_once()
    registry.reset()


async def test_run_sync_refreshes_when_near_expiry(patch_shared) -> None:
    patch_shared.get_token_for_org.return_value = _token_data(
        expires_in_seconds=5  # under the 60s leeway
    )
    refreshed = ProviderConnection(
        access_token="new_at",
        refresh_token="new_rt",
        expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
        scope="read",
        extra={"cloud_id": "cid"},
    )
    adapter = MagicMock()
    adapter.refresh = AsyncMock(return_value=refreshed)
    adapter.sync = AsyncMock(return_value=SyncResult(tickets_upserted=0))
    registry.reset()
    registry.override_for_test("linear", adapter)

    req = sync_mod.SyncRequest(
        org_id=uuid4(), provider="linear", sync_type="delta"
    )
    await sync_mod.run_sync(req)

    adapter.refresh.assert_awaited_once()
    # adapter.sync must be called with the refreshed token, not the stale one
    call_conn = adapter.sync.call_args.args[0]
    assert call_conn.access_token == "new_at"
    patch_shared.store_token.assert_awaited()  # re-persisted
    registry.reset()


async def test_run_sync_revokes_on_refresh_failure(patch_shared) -> None:
    patch_shared.get_token_for_org.return_value = _token_data(
        expires_in_seconds=5
    )
    adapter = MagicMock()
    adapter.refresh = AsyncMock(side_effect=TokenRefreshError("invalid_grant"))
    adapter.sync = AsyncMock()
    registry.reset()
    registry.override_for_test("jira", adapter)

    req = sync_mod.SyncRequest(
        org_id=uuid4(), provider="jira", sync_type="delta"
    )
    with pytest.raises(TokenRefreshError):
        await sync_mod.run_sync(req)

    patch_shared.revoke_token.assert_awaited_once()
    adapter.sync.assert_not_awaited()
    registry.reset()


async def test_run_sync_initial_uses_90d_lookback(patch_shared) -> None:
    patch_shared.get_token_for_org.return_value = _token_data()
    adapter = MagicMock()
    adapter.sync = AsyncMock(return_value=SyncResult())
    adapter.refresh = AsyncMock()
    registry.reset()
    registry.override_for_test("github", adapter)

    req = sync_mod.SyncRequest(
        org_id=uuid4(), provider="github", sync_type="initial_90d"
    )
    await sync_mod.run_sync(req)

    since = adapter.sync.call_args.kwargs["since"]
    expected = datetime.now(tz=UTC) - timedelta(days=90)
    # Allow 30s clock slop
    assert abs((since - expected).total_seconds()) < 30
    registry.reset()
