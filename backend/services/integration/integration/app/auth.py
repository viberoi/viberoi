"""Cognito-based admin auth for Integration service endpoints.

Header: `Authorization: Bearer <Cognito-access-token>`.

`viberoi_shared.cognito.verify_jwt` validates the access token's RS256
signature against the user pool's JWKS, plus `iss` / `client_id` /
`exp` / `token_use`. Custom attributes (`developer_id`, `org_id`,
`role`, `team_id`) are populated by the PostConfirmation Lambda.

Tests still inject synthetic contexts via
`app.dependency_overrides[authenticate]`; the production path runs the
real verifier.
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
)
from viberoi_shared.errors import Forbidden, Unauthorized
from viberoi_shared.logging import bind_request_context, get_logger
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)


@dataclass(frozen=True)
class IntegrationAuthContext:
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


async def authenticate(request: Request) -> IntegrationAuthContext:
    """Parse + verify the Cognito access token; build the auth context.

    Verification failure → `CognitoVerificationError` → handled by the
    global error handler as 401 (no detail leaked).

    Tests override this dependency via
    `app.dependency_overrides[authenticate] = ...`.
    """
    token = _parse_bearer(request)
    try:
        claims: CognitoClaims = await verify_jwt(token)
    except CognitoVerificationError:
        # Don't echo the verifier's error message — caller sees 401.
        raise Unauthorized from None

    ctx = IntegrationAuthContext(
        developer_id=claims.developer_id,
        org_id=claims.org_id,
        role=claims.role,
        team_id=claims.team_id,
    )
    bind_request_context(
        request_id=getattr(request.state, "request_id", "unknown"),
        org_id=str(ctx.org_id),
        developer_id=str(ctx.developer_id),
    )
    logger.info("integration_authenticated", role=ctx.role.value)
    return ctx


AuthRequired = Annotated[IntegrationAuthContext, Depends(authenticate)]


_RoleDep = Callable[..., Coroutine[Any, Any, IntegrationAuthContext]]


def require_role(*allowed: Role) -> _RoleDep:
    """Return a FastAPI dependency that enforces the caller has one of
    the allowed roles."""

    async def _dep(ctx: AuthRequired) -> IntegrationAuthContext:
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
