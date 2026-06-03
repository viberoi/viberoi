"""Sync dispatcher — loads the stored token, lazy-refreshes, runs adapter.sync.

Called from:
  - `app/consumer.py` (drains `backfill_jobs` SQS queue — initial sync after
    OAuth connect + EventBridge-scheduled 5-min delta).
  - `POST /integrations/{provider}/sync` (manual re-trigger).

Idempotent: relies on upsert keying in `viberoi_shared.tickets.repository`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from integration.app.providers import registry
from integration.app.providers.base import (
    ProviderAdapter,
    ProviderConnection,
    SyncResult,
    TokenRefreshError,
)
from viberoi_shared.db import org_scoped_session
from viberoi_shared.errors import NotFound
from viberoi_shared.integrations import (
    get_token_for_org,
    mark_synced,
    revoke_token,
    store_token,
)
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)

REFRESH_LEEWAY_SECONDS = 60
INITIAL_LOOKBACK_DAYS = 90


@dataclass(frozen=True)
class SyncRequest:
    org_id: UUID
    provider: str
    sync_type: str  # "initial_90d" | "delta" | "manual"


async def run_sync(req: SyncRequest) -> SyncResult:
    """Execute one sync for `(org, provider)`. Returns the adapter's SyncResult.

    Raises `NotFound` if the integration is missing or revoked.
    """
    async with org_scoped_session(req.org_id) as db:
        token_data = await get_token_for_org(
            db, org_id=req.org_id, provider=req.provider
        )
    if token_data is None:
        raise NotFound(
            f"No active {req.provider} integration for org {req.org_id}."
        )

    adapter = await registry.get(req.provider)
    connection = _build_connection(token_data)
    connection = await _refresh_if_needed(
        req.org_id, req.provider, adapter, connection, token_data
    )

    since = _compute_since(req, token_data.get("last_sync_at"))
    logger.info(
        "sync_starting",
        provider=req.provider,
        org_id=str(req.org_id),
        sync_type=req.sync_type,
        since=since.isoformat() if since else None,
    )
    result = await adapter.sync(connection, org_id=req.org_id, since=since)

    async with org_scoped_session(req.org_id) as db:
        await mark_synced(db, token_data["id"])

    logger.info(
        "sync_completed",
        provider=req.provider,
        org_id=str(req.org_id),
        tickets=result.tickets_upserted,
        sprints=result.sprints_upserted,
        errors=len(result.errors),
    )
    return result


def _build_connection(token_data: dict) -> ProviderConnection:
    return ProviderConnection(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_at=token_data.get("expires_at"),
        scope=token_data.get("scope"),
        installation_id=token_data.get("installation_id"),
        extra=dict(token_data.get("discovery_metadata") or {}),
    )


async def _refresh_if_needed(
    org_id: UUID,
    provider: str,
    adapter: ProviderAdapter,
    connection: ProviderConnection,
    token_data: dict,
) -> ProviderConnection:
    """If the access token is near expiry, refresh and persist.

    On unrecoverable refresh failure: revoke the local token + raise so the
    caller surfaces 410 to the user (and the SQS message goes to DLQ after
    retries).
    """
    expires_at = connection.expires_at
    if expires_at is None:
        return connection
    if expires_at - datetime.now(tz=UTC) > timedelta(seconds=REFRESH_LEEWAY_SECONDS):
        return connection

    try:
        refreshed = await adapter.refresh(connection)
    except TokenRefreshError:
        async with org_scoped_session(org_id) as db:
            await revoke_token(db, org_id=org_id, provider=provider)
        logger.warning(
            "token_refresh_failed_revoked",
            provider=provider,
            org_id=str(org_id),
        )
        raise

    async with org_scoped_session(org_id) as db:
        await store_token(
            db,
            org_id=org_id,
            provider=provider,
            access_token=refreshed.access_token,
            refresh_token=refreshed.refresh_token,
            webhook_secret=token_data.get("webhook_secret"),
            expires_at=refreshed.expires_at,
            scope=refreshed.scope,
            installation_id=refreshed.installation_id,
            installed_by_developer_id=token_data.get("installed_by_developer_id"),
            discovery_metadata=(
                dict(refreshed.extra)
                if refreshed.extra
                else token_data.get("discovery_metadata")
            ),
        )
    return refreshed


def _compute_since(req: SyncRequest, last_sync_at: datetime | None) -> datetime | None:
    """Initial 90d → None lets the adapter default to 90d.
    Manual / delta → resume from last_sync_at (or 90d if never synced).
    """
    if req.sync_type == "initial_90d":
        return datetime.now(tz=UTC) - timedelta(days=INITIAL_LOOKBACK_DAYS)
    if last_sync_at is None:
        return datetime.now(tz=UTC) - timedelta(days=INITIAL_LOOKBACK_DAYS)
    return last_sync_at
