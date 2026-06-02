"""ORM models for orgs, teams, developers, org_tokens.

Mirrors `backend/migrations/versions/0001_initial_schema.py`. Changes here
need a matching Alembic revision; never edit the DB shape via these models
alone.

PII columns store `(ciphertext, key_version, iv)` triples; the
encryption layer is in `viberoi_shared.crypto`. Lookup columns
(`*_hash`) hold peppered HMAC-SHA256 bytes.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, NUMERIC, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from viberoi_shared.db.base import Base


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    domain: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_ciphertext: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    name_key_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name_iv: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    plan: Mapped[str] = mapped_column(Text, nullable=False, server_default="trial")
    trial_ends_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    billing_email_ciphertext: Mapped[bytes | None] = mapped_column(BYTEA)
    billing_email_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    billing_email_iv: Mapped[bytes | None] = mapped_column(BYTEA)
    billing_email_hash: Mapped[bytes | None] = mapped_column(BYTEA)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_teams_org_name"),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    lead_developer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "developers.id",
            ondelete="SET NULL",
            name="fk_teams_lead_developer",
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class Developer(Base):
    __tablename__ = "developers"
    __table_args__ = (
        UniqueConstraint("org_id", "email_hash", name="uq_developers_org_email"),
        UniqueConstraint(
            "org_id", "machine_id_hash", name="uq_developers_org_machine"
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
    cognito_sub: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    team_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL")
    )
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="Developer")
    # Encrypted PII
    email_ciphertext: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    email_key_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    email_iv: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    email_hash: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    full_name_ciphertext: Mapped[bytes | None] = mapped_column(BYTEA)
    full_name_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    full_name_iv: Mapped[bytes | None] = mapped_column(BYTEA)
    github_username_ciphertext: Mapped[bytes | None] = mapped_column(BYTEA)
    github_username_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    github_username_iv: Mapped[bytes | None] = mapped_column(BYTEA)
    github_username_hash: Mapped[bytes | None] = mapped_column(BYTEA)
    # Non-PII
    hourly_rate_usd: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 2))
    machine_id_hash: Mapped[bytes | None] = mapped_column(BYTEA)
    agent_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    last_active_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class OrgToken(Base):
    __tablename__ = "org_tokens"

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
    developer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="CASCADE"),
        nullable=False,
    )
    hashed: Mapped[str] = mapped_column(Text, nullable=False)  # Argon2id self-describing
    device_label: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    last_used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
