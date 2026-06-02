"""Bearer auth for agent endpoints.

The agent sends three headers:

    Authorization: Bearer <token>
    X-VibeROI-Org-Id: <org_uuid>
    X-VibeROI-Developer-Id: <developer_uuid>

Auth flow:
  1. Parse + validate header shape.
  2. `org_scoped_session(org_id)` — RLS now active.
  3. SELECT developer WHERE id = developer_id (RLS makes this scoped to org).
  4. SELECT non-revoked org_tokens for that developer.
  5. For each, `verify_secret(submitted_token, token.hashed)` — Argon2id.
     If any match → authenticated.
  6. Bind log context (org_id, developer_id) and touch `last_used_at`.

Never reveals which step failed — Unauthorized on every error path.

Future enhancement (deferred to Slice 4+): a separate KMS-encrypted
signing key per token, with `X-VibeROI-Signature` HMAC of the raw body
for defense-in-depth against replay/tampering even when TLS is broken.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select

from viberoi_shared.crypto import verify_secret
from viberoi_shared.db import org_scoped_session
from viberoi_shared.errors import Unauthorized
from viberoi_shared.logging import bind_request_context, get_logger
from viberoi_shared.orgs.models import Developer, OrgToken

logger = get_logger(__name__)


@dataclass(frozen=True)
class AuthContext:
    """Result of a successful authentication."""

    developer_id: UUID
    org_id: UUID


def _parse_auth_headers(request: Request) -> tuple[UUID, UUID, str]:
    """Pure-function parse of the three auth headers.

    Returns `(org_id, developer_id, token)`. Raises `Unauthorized` on
    any missing/malformed input (so callers don't need to handle
    multiple exception types).
    """
    authz = request.headers.get("authorization", "")
    org_id_raw = request.headers.get("x-viberoi-org-id", "")
    dev_id_raw = request.headers.get("x-viberoi-developer-id", "")

    if not authz.lower().startswith("bearer "):
        raise Unauthorized
    token = authz[7:].strip()
    if not token:
        raise Unauthorized

    try:
        org_uuid = UUID(org_id_raw)
        developer_uuid = UUID(dev_id_raw)
    except (ValueError, TypeError) as e:
        raise Unauthorized from e

    return org_uuid, developer_uuid, token


async def authenticate(request: Request) -> AuthContext:
    """Authenticate the request. Returns AuthContext or raises Unauthorized."""
    org_uuid, developer_uuid, token = _parse_auth_headers(request)

    # RLS-scoped lookup: a developer claiming org A cannot be found from
    # an org-B-scoped session even if the dev id is valid in org B.
    async with org_scoped_session(org_uuid) as db:
        dev = await db.get(Developer, developer_uuid)
        if dev is None:
            raise Unauthorized

        stmt = (
            select(OrgToken)
            .where(OrgToken.developer_id == developer_uuid)
            .where(OrgToken.revoked_at.is_(None))
        )
        result = await db.execute(stmt)
        tokens = list(result.scalars().all())

    matched: OrgToken | None = None
    for candidate in tokens:
        if verify_secret(token, candidate.hashed):
            matched = candidate
            break

    if matched is None:
        raise Unauthorized

    bind_request_context(
        request_id=getattr(request.state, "request_id", "unknown"),
        org_id=str(org_uuid),
        developer_id=str(developer_uuid),
    )
    logger.info("agent_authenticated")

    # Best-effort touch of last_used_at. A failure here doesn't fail the
    # request — the agent already succeeded.
    try:
        async with org_scoped_session(org_uuid) as db:
            fresh = await db.get(OrgToken, matched.id)
            if fresh is not None:
                fresh.last_used_at = datetime.now(tz=UTC)
    except Exception:  # noqa: BLE001, S110
        logger.warning("touch_last_used_at_failed", token_id=str(matched.id))

    return AuthContext(developer_id=developer_uuid, org_id=org_uuid)


# Type alias for FastAPI handler signatures.
AuthRequired = Annotated[AuthContext, Depends(authenticate)]
