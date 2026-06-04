"""Cognito access-token auth for API endpoints.

Header: `Authorization: Bearer <Cognito-access-token>`.

`viberoi_shared.cognito.verify_jwt` validates the token; this module
wraps the result in `ApiAuthContext` and exposes `require_role` for
per-route RBAC. Tests inject synthetic contexts via
`app.dependency_overrides[authenticate]`.

Dev-mode passthrough
--------------------
When `settings.env == Env.DEV`, requests carrying `X-Dev-Org-Id` /
`X-Dev-Developer-Id` / `X-Dev-Role` / optional `X-Dev-Team-Id` headers
short-circuit JWT validation and build an `ApiAuthContext` directly
from the header values. This unblocks the dev frontend (Slice 5D)
before real Cognito is provisioned in Slice 6.

The dev path is GATED on `settings.env`. Production never reaches the
passthrough — `verify_jwt` is the only auth source there.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request

from viberoi_shared.cognito import (
    CognitoClaims,
    CognitoVerificationError,
    verify_jwt,
    verify_jwt_basic,
)
from viberoi_shared.config import Env, get_settings
from viberoi_shared.db import superuser_session
from viberoi_shared.errors import Forbidden, Unauthorized
from viberoi_shared.logging import bind_request_context, get_logger
from viberoi_shared.orgs import get_developer_by_cognito_sub
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)


@dataclass(frozen=True)
class ApiAuthContext:
    developer_id: UUID
    org_id: UUID
    role: Role
    team_id: UUID | None


def _parse_bearer(request: Request) -> str:
    authz = request.headers.get("authorization", "")
    if not authz.lower().startswith("bearer "):
        raise Unauthorized
    token = authz[7:].strip()
    if not token:
        raise Unauthorized
    return token


def _try_dev_passthrough(request: Request) -> ApiAuthContext | None:
    """Dev-only auth path. Returns the constructed context if the request
    carries the dev headers AND the environment is `dev`. Otherwise
    returns None and lets the caller fall through to JWT verification.
    """
    if get_settings().env != Env.DEV:
        return None
    org_header = request.headers.get("x-dev-org-id")
    dev_header = request.headers.get("x-dev-developer-id")
    role_header = request.headers.get("x-dev-role")
    if not org_header or not dev_header or not role_header:
        return None
    try:
        ctx = ApiAuthContext(
            developer_id=UUID(dev_header),
            org_id=UUID(org_header),
            role=Role(role_header),
            team_id=UUID(request.headers["x-dev-team-id"])
            if request.headers.get("x-dev-team-id")
            else None,
        )
    except (ValueError, KeyError):
        # Malformed dev header → fall through; verify_jwt will reject too.
        return None
    logger.info("api_dev_auth_passthrough", role=ctx.role.value)
    return ctx


async def authenticate(request: Request) -> ApiAuthContext:
    """Parse + verify the Cognito access token; build the auth context.

    Three-step fallback:
      1. Dev passthrough (X-Dev-* headers, gated on env=dev).
      2. `verify_jwt` (full path) — requires `custom:org_id`/`role` claims
         set by the PreTokenGeneration Lambda. Production default.
      3. `verify_jwt_basic` + DB lookup by `sub` — used when the Lambda
         is not yet deployed (early dev). Looks up org/role from the
         developers table via the sub. Equivalent security: the JWT is
         still signature-verified; we just source authorization data
         from the DB rather than from token claims.

    Verification failure on every path → `Unauthorized` (no detail leak).
    """
    dev_ctx = _try_dev_passthrough(request)
    if dev_ctx is not None:
        ctx = dev_ctx
    else:
        token = _parse_bearer(request)
        ctx = await _resolve_jwt_ctx(token)

    bind_request_context(
        request_id=getattr(request.state, "request_id", "unknown"),
        org_id=str(ctx.org_id),
        developer_id=str(ctx.developer_id),
    )
    logger.info("api_authenticated", role=ctx.role.value)
    return ctx


async def _resolve_jwt_ctx(token: str) -> ApiAuthContext:
    """Try the claims-rich path first; fall back to sub→DB lookup."""
    try:
        claims: CognitoClaims = await verify_jwt(token)
        return ApiAuthContext(
            developer_id=claims.developer_id,
            org_id=claims.org_id,
            role=claims.role,
            team_id=claims.team_id,
        )
    except CognitoVerificationError:
        # Custom attrs missing — likely the PreTokenGeneration Lambda
        # isn't deployed yet. Fall through to the DB-lookup path.
        pass

    try:
        raw = await verify_jwt_basic(token)
    except CognitoVerificationError:
        raise Unauthorized from None

    sub = raw["sub"]
    # Cross-org lookup — by definition we don't yet know which org the
    # caller belongs to. superuser_session bypasses RLS for this one
    # bootstrap query; the request switches to org-scoped sessions after.
    async with superuser_session() as db:
        dev = await get_developer_by_cognito_sub(db, sub)
    if dev is None:
        logger.warning("cognito_sub_unknown", sub_prefix=sub[:8])
        raise Unauthorized

    try:
        role = Role(dev.role)
    except ValueError:
        raise Unauthorized from None

    return ApiAuthContext(
        developer_id=dev.id,
        org_id=dev.org_id,
        role=role,
        team_id=dev.team_id,
    )


AuthRequired = Annotated[ApiAuthContext, Depends(authenticate)]


_RoleDep = Callable[..., Coroutine[Any, Any, ApiAuthContext]]


def require_role(*allowed: Role) -> _RoleDep:
    """Return a FastAPI dependency that enforces the caller has one of
    the allowed roles."""

    async def _dep(ctx: AuthRequired) -> ApiAuthContext:
        if ctx.role not in allowed:
            logger.warning(
                "rbac_denied",
                role=ctx.role.value,
                allowed=[r.value for r in allowed],
            )
            raise Forbidden(
                f"Role '{ctx.role.value}' not permitted for this endpoint."
            )
        return ctx

    return _dep
