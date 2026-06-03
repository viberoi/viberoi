"""CRUD functions for orgs, teams, developers, org_tokens.

PII fields handled here are still raw bytes — the encryption/decryption
layer sits on top in `viberoi_shared.crypto` (lands with KMS envelope
in Slice 5). Callers pass already-encrypted values.

Lookup-by-PII goes via the matching `*_hash` column (peppered HMAC,
see `viberoi_shared.crypto.lookup`) — never by decrypting.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
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


async def create_org_if_missing(
    db: AsyncSession,
    *,
    domain: str,
    name_ciphertext: bytes,
    name_key_version: int,
    name_iv: bytes,
) -> Org:
    """Idempotent org create — used by PostConfirmation Lambda.

    Inserts a new org for `domain` (lowercased). If a row already exists,
    returns the existing row without modifying it.
    """
    domain = domain.lower()
    values: dict[str, Any] = {
        "domain": domain,
        "name_ciphertext": name_ciphertext,
        "name_key_version": name_key_version,
        "name_iv": name_iv,
    }
    stmt = (
        insert(Org)
        .values(values)
        .on_conflict_do_nothing(index_elements=["domain"])
        .returning(Org.id)
    )
    result = await db.execute(stmt)
    new_id = result.scalar_one_or_none()
    if new_id is not None:
        await db.flush()
        org = await db.get(Org, new_id)
        if org is not None:
            return org
    existing = await get_org_by_domain(db, domain)
    if existing is None:
        raise NotFound(f"Could not create or locate org for domain {domain}")
    return existing


async def create_developer_if_missing(
    db: AsyncSession,
    *,
    org_id: UUID,
    cognito_sub: str,
    role: str,
    email_ciphertext: bytes,
    email_key_version: int,
    email_iv: bytes,
    email_hash: bytes,
) -> Developer:
    """Idempotent developer create keyed on `cognito_sub`.

    PostConfirmation may fire more than once per user (Cognito does not
    guarantee exactly-once trigger delivery). Re-running must return the
    existing row, not duplicate it.
    """
    values: dict[str, Any] = {
        "org_id": org_id,
        "cognito_sub": cognito_sub,
        "role": role,
        "email_ciphertext": email_ciphertext,
        "email_key_version": email_key_version,
        "email_iv": email_iv,
        "email_hash": email_hash,
    }
    stmt = (
        insert(Developer)
        .values(values)
        .on_conflict_do_nothing(index_elements=["cognito_sub"])
        .returning(Developer.id)
    )
    result = await db.execute(stmt)
    new_id = result.scalar_one_or_none()
    if new_id is not None:
        await db.flush()
        dev = await db.get(Developer, new_id)
        if dev is not None:
            return dev
    existing = await get_developer_by_cognito_sub(db, cognito_sub)
    if existing is None:
        raise NotFound(
            f"Could not create or locate developer for cognito_sub {cognito_sub}"
        )
    return existing


async def count_developers(db: AsyncSession, org_uuid: UUID) -> int:
    """How many developers an org has — used by PostConfirmation to assign
    `OrgAdmin` to the first user and `Developer` to subsequent invitees."""
    stmt = select(func.count(Developer.id)).where(Developer.org_id == org_uuid)
    result = await db.execute(stmt)
    return int(result.scalar_one())


async def lock_org_for_update(db: AsyncSession, org_uuid: UUID) -> Org:
    """`SELECT ... FOR UPDATE` on the org row.

    Used by PostConfirmation to serialize role assignment across two
    concurrent first-time signups for the same domain — without this
    lock both can read `count_developers == 0` and both become
    OrgAdmin. The lock releases when the transaction commits.
    """
    stmt = select(Org).where(Org.id == org_uuid).with_for_update()
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFound(f"Org {org_uuid} not found")
    return row
