"""Org-scoped AsyncSession with mandatory RLS context.

Services obtain DB sessions EXCLUSIVELY via `org_scoped_session(org_id)`.
The helper sets `app.current_org_id` inside the transaction, so Postgres
RLS enforces tenant isolation even if app code forgets to filter.

Usage:
    async with org_scoped_session(org_id) as db:
        await sessions.create(db, payload)
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from viberoi_shared.db.engine import get_session_factory
from viberoi_shared.errors.types import VibeRoiError


class OrgContextError(VibeRoiError):
    code = "org_context_error"
    safe_message = "Org context could not be established."


def _validate_org_id(org_id: str | UUID) -> str:
    """Coerce to a canonical UUID string; reject invalid input.

    Validating to UUID before passing to `set_config` prevents any
    SQL injection through the GUC value.
    """
    try:
        return str(UUID(str(org_id)))
    except (ValueError, AttributeError) as e:
        raise OrgContextError(f"Invalid org_id: {org_id!r}") from e


@asynccontextmanager
async def org_scoped_session(org_id: str | UUID) -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession with `app.current_org_id` set for RLS.

    The GUC is set via `set_config(..., is_local=true)` inside a
    transaction, so it's automatically cleared when the transaction
    ends. The connection returns clean to the pool.

    Refuses to proceed without a valid UUID — guards the most
    likely RLS-bypass bug (passing `None` or an attacker-supplied string).
    """
    safe_org_id = _validate_org_id(org_id)
    factory = get_session_factory()

    async with factory() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_org_id', :oid, true)"),
                {"oid": safe_org_id},
            )
            yield session


@asynccontextmanager
async def superuser_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession without org context.

    Use ONLY for cross-org admin tasks (migrations, cross-org KPI
    crons, scheduled cleanups). Never expose to request handlers.

    The migration grants this role `BYPASSRLS`. RLS policies should
    deny by default when `app.current_org_id` is unset, so this
    session is the only legitimate path to cross-tenant reads.
    """
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            yield session
