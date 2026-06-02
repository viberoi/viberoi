"""ORM for the `integration_oauth_tokens` table.

Mirrors migration `0004_tickets_sprints_oauth.py`. All token + secret
fields use the `(ciphertext, key_version, iv)` shape; see
`.claude/rules/security.md` and `viberoi_shared.crypto.envelope`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from viberoi_shared.db.base import Base


class IntegrationOAuthToken(Base):
    __tablename__ = "integration_oauth_tokens"
    __table_args__ = (
        UniqueConstraint("org_id", "provider", name="uq_oauth_org_provider"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)

    # Encrypted access token (mandatory)
    access_token_ciphertext: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    access_token_key_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    access_token_iv: Mapped[bytes] = mapped_column(BYTEA, nullable=False)

    # Encrypted refresh token (some flows don't issue one)
    refresh_token_ciphertext: Mapped[bytes | None] = mapped_column(BYTEA)
    refresh_token_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    refresh_token_iv: Mapped[bytes | None] = mapped_column(BYTEA)

    # Encrypted webhook signing secret (used by the webhook Lambda's HMAC verify)
    webhook_secret_ciphertext: Mapped[bytes | None] = mapped_column(BYTEA)
    webhook_secret_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    webhook_secret_iv: Mapped[bytes | None] = mapped_column(BYTEA)

    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    scope: Mapped[str | None] = mapped_column(Text)
    installation_id: Mapped[str | None] = mapped_column(Text)
    installed_by_developer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Post-OAuth metadata (added in migration 0005)
    discovery_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    webhook_registration_status: Mapped[str | None] = mapped_column(Text)
    last_sync_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    webhook_ids: Mapped[list[str] | None] = mapped_column(JSONB)
