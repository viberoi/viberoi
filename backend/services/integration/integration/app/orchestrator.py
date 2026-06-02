"""High-level orchestration for the Integration service.

Stitches together:
  - OAuth state (Redis) for CSRF binding
  - Per-provider OAuth flows (adapters)
  - Token storage (encrypted via shared.integrations)
  - Webhook registration on the provider side
  - SQS enqueue for the initial backfill (consumer lands in C5)

Failures partway through are recoverable: if webhook registration fails
after the token is stored, the integration row has
`webhook_registration_status='failed'` and `/sync` can re-attempt.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from integration.app.providers import registry
from integration.app.providers.base import (
    ProviderConnection,
    WebhookRegistrationError,
)
from viberoi_shared.db import org_scoped_session
from viberoi_shared.errors import NotFound
from viberoi_shared.integrations import (
    get_token_for_org,
    list_for_org,
    oauth_state,
    revoke_token,
    store_token,
    update_webhook_metadata,
)
from viberoi_shared.integrations.oauth_state import OAuthStateError
from viberoi_shared.logging import get_logger
from viberoi_shared.sqs import publish as sqs_publish

logger = get_logger(__name__)

# Queue the backfill consumer (Slice 4 C5) drains.
BACKFILL_QUEUE = "backfill_jobs"


@dataclass(frozen=True)
class InitiateResult:
    authorize_url: str


@dataclass(frozen=True)
class CompleteResult:
    integration_id: UUID
    webhook_registration_status: str  # "ok" | "failed"


# ── initiate_connect ───────────────────────────────────────────────────────


async def initiate_connect(
    *,
    org_id: UUID,
    developer_id: UUID,
    provider: str,
    redirect_uri: str,
) -> InitiateResult:
    """Mint state, persist to Redis, build the provider's authorize URL."""
    adapter = await registry.get(provider)
    state = oauth_state.generate_token()
    await oauth_state.store(
        state, org_id=org_id, developer_id=developer_id, provider=provider
    )
    url = adapter.authorize_url(state=state, redirect_uri=redirect_uri)
    logger.info(
        "oauth_initiated",
        provider=provider,
        org_id=str(org_id),
        developer_id=str(developer_id),
    )
    return InitiateResult(authorize_url=url)


# ── complete_connect ───────────────────────────────────────────────────────


async def complete_connect(
    *,
    provider: str,
    callback_params: dict[str, str],
    redirect_uri: str,
    webhook_base_url: str,
) -> CompleteResult:
    """Process the provider's callback: state verify → token exchange →
    persist → webhook register → enqueue initial backfill."""
    state = callback_params.get("state", "")
    payload = await oauth_state.consume(state)
    if payload.get("provider") != provider:
        raise OAuthStateError("OAuth state provider mismatch.")

    org_id = UUID(payload["org_id"])
    developer_id = UUID(payload["developer_id"])

    adapter = await registry.get(provider)
    connection = await adapter.complete_callback(
        callback_params, redirect_uri=redirect_uri
    )

    # Persist the OAuth token first — the integration_id we get back goes
    # into the webhook URL.
    async with org_scoped_session(org_id) as db:
        integration_id = await store_token(
            db,
            org_id=org_id,
            provider=provider,
            access_token=connection.access_token,
            refresh_token=connection.refresh_token,
            expires_at=connection.expires_at,
            scope=connection.scope,
            installation_id=connection.installation_id,
            installed_by_developer_id=developer_id,
            discovery_metadata=dict(connection.extra),
        )

    # Register the webhook on the provider side. Failure here is recoverable:
    # the row stays with webhook_registration_status='failed' and the user
    # can re-run /sync to re-attempt.
    webhook_url = f"{webhook_base_url}/webhooks/{provider}/{integration_id}"
    webhook_secret = secrets.token_urlsafe(32)
    registration_status = "failed"
    webhook_ids: list[str] = []
    stored_secret: str | None = None

    try:
        webhook_reg = await adapter.register_webhook(
            connection, webhook_url=webhook_url, secret=webhook_secret
        )
        registration_status = "ok"
        webhook_ids = webhook_reg.provider_webhook_ids
        # Some providers (Jira OAuth 2.0) don't accept an HMAC secret and
        # return "" — don't persist a secret that won't ever verify a
        # webhook.
        stored_secret = webhook_reg.secret if webhook_reg.secret else None
    except WebhookRegistrationError as e:
        logger.warning(
            "webhook_registration_failed",
            provider=provider,
            org_id=str(org_id),
            error=str(e),
        )

    async with org_scoped_session(org_id) as db:
        await update_webhook_metadata(
            db,
            integration_id=integration_id,
            webhook_secret=stored_secret,
            webhook_ids=webhook_ids,
            status=registration_status,
        )

    # Initial backfill — consumer lands in Slice 4 C5.
    trace_id = str(uuid4())
    await sqs_publish(
        BACKFILL_QUEUE,
        {
            "org_id": str(org_id),
            "provider": provider,
            "sync_type": "initial_90d",
            "requested_by": str(developer_id),
            "trace_id": trace_id,
        },
    )

    logger.info(
        "oauth_completed",
        provider=provider,
        org_id=str(org_id),
        integration_id=str(integration_id),
        webhook_status=registration_status,
        trace_id=trace_id,
    )
    return CompleteResult(
        integration_id=integration_id,
        webhook_registration_status=registration_status,
    )


# ── disconnect ─────────────────────────────────────────────────────────────


async def disconnect(*, org_id: UUID, provider: str) -> None:
    """Revoke + provider-side cleanup. Local revoke is the source of truth;
    provider-side failures are logged but don't block."""
    async with org_scoped_session(org_id) as db:
        token_data = await get_token_for_org(db, org_id=org_id, provider=provider)

    if token_data is None:
        raise NotFound(f"No active {provider} integration for this org.")

    try:
        adapter = await registry.get(provider)
        connection = ProviderConnection(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=token_data.get("expires_at"),
            installation_id=token_data.get("installation_id"),
            extra={
                **(token_data.get("discovery_metadata") or {}),
                "webhook_ids": token_data.get("webhook_ids") or [],
            },
        )
        await adapter.revoke(connection)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "provider_revoke_failed",
            provider=provider,
            org_id=str(org_id),
            error=str(e),
        )

    async with org_scoped_session(org_id) as db:
        await revoke_token(db, org_id=org_id, provider=provider)

    logger.info(
        "integration_disconnected",
        provider=provider,
        org_id=str(org_id),
    )


# ── list_integrations ──────────────────────────────────────────────────────


async def list_integrations(*, org_id: UUID) -> list[dict[str, Any]]:
    """Return a summary row per integration. Used by `GET /integrations`."""
    async with org_scoped_session(org_id) as db:
        rows = await list_for_org(db, org_id, include_revoked=False)
    return [
        {
            "id": row.id,
            "provider": row.provider,
            "installed_by_developer_id": row.installed_by_developer_id,
            "expires_at": row.expires_at,
            "scope": row.scope,
            "created_at": row.created_at,
            "webhook_registration_status": row.webhook_registration_status,
            "last_sync_at": row.last_sync_at,
            "revoked": row.revoked_at is not None,
        }
        for row in rows
    ]
