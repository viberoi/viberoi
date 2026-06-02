"""CRUD functions for orgs, teams, developers, org_tokens.

PII fields handled here are still raw bytes — the encryption/decryption
layer sits on top in `viberoi_shared.crypto` (lands with KMS envelope
in Slice 5). Callers pass already-encrypted values.

Lookup-by-PII goes via the matching `*_hash` column (peppered HMAC,
see `viberoi_shared.crypto.lookup`) — never by decrypting.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viberoi_shared.errors.types import NotFound
from viberoi_shared.orgs.models import Developer, Org, OrgToken, Team


async def get_org(db: AsyncSession, org_uuid: UUID) -> Org:
    row = await db.get(Org, org_uuid)
    if row is None:
        raise NotFound(f"Org {org_uuid} not found")
    return row


async def get_org_by_domain(db: AsyncSession, domain: str) -> Org | None:
    """Used by the Cognito PreSignUp Lambda for the one-org-per-domain check."""
    stmt = select(Org).where(Org.domain == domain.lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_developer(db: AsyncSession, developer_uuid: UUID) -> Developer:
    row = await db.get(Developer, developer_uuid)
    if row is None:
        raise NotFound(f"Developer {developer_uuid} not found")
    return row


async def get_developer_by_cognito_sub(
    db: AsyncSession, cognito_sub: str
) -> Developer | None:
    stmt = select(Developer).where(Developer.cognito_sub == cognito_sub)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_developer_by_email_hash(
    db: AsyncSession, *, org_uuid: UUID, email_hash: bytes
) -> Developer | None:
    """Lookup developer by email without decrypting the email column."""
    stmt = select(Developer).where(
        Developer.org_id == org_uuid,
        Developer.email_hash == email_hash,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_org_token(db: AsyncSession, token_uuid: UUID) -> OrgToken:
    row = await db.get(OrgToken, token_uuid)
    if row is None:
        raise NotFound(f"OrgToken {token_uuid} not found")
    return row


async def list_teams(db: AsyncSession, org_uuid: UUID) -> list[Team]:
    stmt = select(Team).where(Team.org_id == org_uuid).order_by(Team.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())
