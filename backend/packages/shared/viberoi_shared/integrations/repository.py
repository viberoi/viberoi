"""OAuth token storage + retrieval — encrypts on write, decrypts on read.

Functions return plaintext tokens to the caller; persistence is always
encrypted. The caller is responsible for not logging the plaintext.

Encryption context binds the ciphertext to its row + field, so copying
a ciphertext to a different org/field can't decrypt.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from viberoi_shared.crypto import decrypt_pii, encrypt_pii
from viberoi_shared.crypto.envelope import EncryptedField
from viberoi_shared.errors.types import NotFound
from viberoi_shared.integrations.models import IntegrationOAuthToken


def _context(org_id: UUID, provider: str, field: str) -> str:
    return f"org:{org_id}:integration:{provider}:field:{field}"


async def store_token(
    db: AsyncSession,
    *,
    org_id: UUID,
    provider: str,
    access_token: str,
    refresh_token: str | None = None,
    webhook_secret: str | None = None,
    expires_at: datetime | None = None,
    scope: str | None = None,
    installation_id: str | None = None,
    installed_by_developer_id: UUID | None = None,
    discovery_metadata: dict[str, Any] | None = None,
) -> UUID:
    """Upsert an OAuth token for `(org_id, provider)`. Returns the row id.

    Each secret is encrypted with an AAD bound to `(org_id, provider, field)`
    — preventing ciphertext reuse across rows / fields.

    `discovery_metadata` is a non-secret per-provider blob (Jira cloud_id +
    sprint_field_id, Linear organization_id, GitHub repository_selection)
    stored in the JSONB column added by migration 0005.
    """
    access = await encrypt_pii(
        access_token, context=_context(org_id, provider, "access_token")
    )

    refresh: EncryptedField | None = None
    if refresh_token:
        refresh = await encrypt_pii(
            refresh_token, context=_context(org_id, provider, "refresh_token")
        )

    webhook: EncryptedField | None = None
    if webhook_secret:
        webhook = await encrypt_pii(
            webhook_secret, context=_context(org_id, provider, "webhook_secret")
        )

    values: dict[str, Any] = {
        "org_id": org_id,
        "provider": provider,
        "access_token_ciphertext": access.ciphertext,
        "access_token_key_version": access.key_version,
        "access_token_iv": access.iv,
        "refresh_token_ciphertext": refresh.ciphertext if refresh else None,
        "refresh_token_key_version": refresh.key_version if refresh else None,
        "refresh_token_iv": refresh.iv if refresh else None,
        "webhook_secret_ciphertext": webhook.ciphertext if webhook else None,
        "webhook_secret_key_version": webhook.key_version if webhook else None,
        "webhook_secret_iv": webhook.iv if webhook else None,
        "expires_at": expires_at,
        "scope": scope,
        "installation_id": installation_id,
        "installed_by_developer_id": installed_by_developer_id,
        "revoked_at": None,
        "discovery_metadata": discovery_metadata,
    }
    stmt = insert(IntegrationOAuthToken).values(values)
    update_cols = {
        col: stmt.excluded[col] for col in values if col not in {"org_id", "provider"}
    }
    stmt = stmt.on_conflict_do_update(
        constraint="uq_oauth_org_provider", set_=update_cols
    ).returning(IntegrationOAuthToken.id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_token_for_org(
    db: AsyncSession, *, org_id: UUID, provider: str
) -> dict[str, Any] | None:
    """Return a dict with decrypted tokens + metadata, or None if not present
    or revoked.

    Keys:
      access_token, refresh_token (str|None), webhook_secret (str|None),
      expires_at, scope, installation_id, installed_by_developer_id, created_at
    """
    stmt = select(IntegrationOAuthToken).where(
        IntegrationOAuthToken.org_id == org_id,
        IntegrationOAuthToken.provider == provider,
        IntegrationOAuthToken.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None

    access = await decrypt_pii(
        EncryptedField(
            ciphertext=row.access_token_ciphertext,
            key_version=row.access_token_key_version,
            iv=row.access_token_iv,
        ),
        context=_context(org_id, provider, "access_token"),
    )

    refresh: str | None = None
    if row.refresh_token_ciphertext is not None:
        refresh = await decrypt_pii(
            EncryptedField(
                ciphertext=row.refresh_token_ciphertext,
                key_version=row.refresh_token_key_version or 1,
                iv=row.refresh_token_iv or b"",
            ),
            context=_context(org_id, provider, "refresh_token"),
        )

    webhook: str | None = None
    if row.webhook_secret_ciphertext is not None:
        webhook = await decrypt_pii(
            EncryptedField(
                ciphertext=row.webhook_secret_ciphertext,
                key_version=row.webhook_secret_key_version or 1,
                iv=row.webhook_secret_iv or b"",
            ),
            context=_context(org_id, provider, "webhook_secret"),
        )

    return {
        "id": row.id,
        "access_token": access,
        "refresh_token": refresh,
        "webhook_secret": webhook,
        "expires_at": row.expires_at,
        "scope": row.scope,
        "installation_id": row.installation_id,
        "installed_by_developer_id": row.installed_by_developer_id,
        "created_at": row.created_at,
        "discovery_metadata": row.discovery_metadata or {},
        "webhook_registration_status": row.webhook_registration_status,
        "webhook_ids": row.webhook_ids or [],
        "last_sync_at": row.last_sync_at,
    }


async def list_for_org(
    db: AsyncSession, org_id: UUID, *, include_revoked: bool = False
) -> list[IntegrationOAuthToken]:
    """All integrations for an org. Used by `GET /integrations`."""
    stmt = select(IntegrationOAuthToken).where(
        IntegrationOAuthToken.org_id == org_id
    )
    if not include_revoked:
        stmt = stmt.where(IntegrationOAuthToken.revoked_at.is_(None))
    stmt = stmt.order_by(IntegrationOAuthToken.provider)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_webhook_metadata(
    db: AsyncSession,
    *,
    integration_id: UUID,
    webhook_secret: str | None,
    webhook_ids: list[str] | None,
    status: str,
) -> None:
    """Persist webhook registration outcome after the provider call returns.

    `webhook_secret` is encrypted via KMS envelope if non-empty; `None`
    or `""` skips the secret update (Jira doesn't use one).
    `webhook_ids` is JSONB; `status` is `pending | ok | failed`.
    """
    row = await db.get(IntegrationOAuthToken, integration_id)
    if row is None:
        raise NotFound(f"IntegrationOAuthToken {integration_id} not found")

    values: dict[str, Any] = {
        "webhook_registration_status": status,
        "webhook_ids": webhook_ids or [],
        "updated_at": datetime.now(tz=UTC),
    }

    if webhook_secret:
        encrypted = await encrypt_pii(
            webhook_secret,
            context=_context(row.org_id, row.provider, "webhook_secret"),
        )
        values["webhook_secret_ciphertext"] = encrypted.ciphertext
        values["webhook_secret_key_version"] = encrypted.key_version
        values["webhook_secret_iv"] = encrypted.iv

    stmt = (
        update(IntegrationOAuthToken)
        .where(IntegrationOAuthToken.id == integration_id)
        .values(**values)
    )
    await db.execute(stmt)


async def mark_synced(db: AsyncSession, integration_id: UUID) -> None:
    """Update `last_sync_at` to now. Called by the backfill consumer."""
    stmt = (
        update(IntegrationOAuthToken)
        .where(IntegrationOAuthToken.id == integration_id)
        .values(last_sync_at=datetime.now(tz=UTC))
    )
    await db.execute(stmt)


async def get_token_record(
    db: AsyncSession, token_uuid: UUID
) -> IntegrationOAuthToken:
    row = await db.get(IntegrationOAuthToken, token_uuid)
    if row is None:
        raise NotFound(f"IntegrationOAuthToken {token_uuid} not found")
    return row


async def revoke_token(
    db: AsyncSession, *, org_id: UUID, provider: str
) -> bool:
    """Mark a token revoked. Returns True if a row was updated."""
    stmt = (
        update(IntegrationOAuthToken)
        .where(
            IntegrationOAuthToken.org_id == org_id,
            IntegrationOAuthToken.provider == provider,
            IntegrationOAuthToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(tz=UTC))
    )
    result = await db.execute(stmt)
    return result.rowcount > 0
