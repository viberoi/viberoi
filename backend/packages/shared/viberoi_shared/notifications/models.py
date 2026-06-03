"""ORM model for notification_channels.

Mirrors `backend/migrations/versions/0006_notification_channels.py`.
The webhook_url envelope (ciphertext + key_version + iv) is decrypted
on demand inside the Notification consumer; nothing else in the
codebase decrypts these.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from viberoi_shared.db.base import Base


class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "channel", name="uq_notification_channels_org_channel"
        ),
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
    channel: Mapped[str] = mapped_column(Text, nullable=False)

    webhook_url_ciphertext: Mapped[bytes | None] = mapped_column(BYTEA)
    webhook_url_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    webhook_url_iv: Mapped[bytes | None] = mapped_column(BYTEA)

    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
