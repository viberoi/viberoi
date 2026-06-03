"""CRUD for notification_channels — encrypted webhook URLs.

Encryption context binds the ciphertext to its `(org_id, channel, field)`
tuple, so a Slack URL copied to a Teams row can't decrypt — same
pattern as `viberoi_shared.integrations.repository`.
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
from viberoi_shared.errors.types import NotFound, ValidationFailed
from viberoi_shared.notifications.guards import assert_safe_slack_webhook_url
from viberoi_shared.notifications.models import NotificationChannel


def _context(org_id: UUID, channel: str, field: str) -> str:
    return f"org:{org_id}:notification:{channel}:field:{field}"


async def upsert_channel(
    db: AsyncSession,
    *,
    org_id: UUID,
    channel: str,
    webhook_url: str | None = None,
    config: dict[str, Any] | None = None,
    enabled: bool = True,
) -> UUID:
    """Insert or update a channel for `(org_id, channel)`. Returns row id.

    Encrypts `webhook_url` if provided; leaves the envelope columns NULL
    otherwise (email channels that store recipients in `config_json`).
    """
    values: dict[str, Any] = {
        "org_id": org_id,
        "channel": channel,
        "config_json": config,
        "enabled": enabled,
        "webhook_url_ciphertext": None,
        "webhook_url_key_version": None,
        "webhook_url_iv": None,
    }

    if webhook_url is not None:
        # SSRF guard at write time — block bad URLs before they can ever
        # reach the consumer. The consumer also re-checks at delivery time.
        if channel == "slack":
            try:
                assert_safe_slack_webhook_url(webhook_url)
            except ValueError as e:
                raise ValidationFailed(str(e)) from e
        enc = await encrypt_pii(
            webhook_url, context=_context(org_id, channel, "webhook_url")
        )
        values["webhook_url_ciphertext"] = enc.ciphertext
        values["webhook_url_key_version"] = enc.key_version
        values["webhook_url_iv"] = enc.iv

    stmt = insert(NotificationChannel).values(values)
    update_cols = {
        col: stmt.excluded[col] for col in values if col not in {"org_id", "channel"}
    }
    update_cols["updated_at"] = datetime.now(tz=UTC)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_notification_channels_org_channel", set_=update_cols
    ).returning(NotificationChannel.id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_channel_for_org(
    db: AsyncSession, *, org_id: UUID, channel: str
) -> dict[str, Any] | None:
    """Return decrypted channel config, or None if missing / disabled.

    Caller MUST NOT log the returned `webhook_url`.
    """
    stmt = select(NotificationChannel).where(
        NotificationChannel.org_id == org_id,
        NotificationChannel.channel == channel,
        NotificationChannel.enabled.is_(True),
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None

    webhook_url: str | None = None
    if row.webhook_url_ciphertext is not None:
        webhook_url = await decrypt_pii(
            EncryptedField(
                ciphertext=row.webhook_url_ciphertext,
                key_version=row.webhook_url_key_version or 1,
                iv=row.webhook_url_iv or b"",
            ),
            context=_context(org_id, channel, "webhook_url"),
        )

    return {
        "id": row.id,
        "channel": row.channel,
        "webhook_url": webhook_url,
        "config": row.config_json or {},
        "enabled": row.enabled,
    }


async def disable_channel(
    db: AsyncSession, *, org_id: UUID, channel: str
) -> bool:
    """Soft-disable. Used by the Notification consumer's circuit breaker
    after `MAX_FAILURES_BEFORE_DISABLE` consecutive failures."""
    stmt = (
        update(NotificationChannel)
        .where(
            NotificationChannel.org_id == org_id,
            NotificationChannel.channel == channel,
        )
        .values(enabled=False, updated_at=datetime.now(tz=UTC))
    )
    result = await db.execute(stmt)
    return result.rowcount > 0


async def get_channel_record(
    db: AsyncSession, channel_uuid: UUID
) -> NotificationChannel:
    row = await db.get(NotificationChannel, channel_uuid)
    if row is None:
        raise NotFound(f"NotificationChannel {channel_uuid} not found")
    return row
