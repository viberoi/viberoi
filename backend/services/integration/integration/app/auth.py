"""Cognito-based admin auth for Integration service endpoints.

Header: `Authorization: Bearer <Cognito-JWT>`.

`viberoi_shared.cognito.verify_jwt` is stubbed (raises until Slice 5).
For development + tests, use FastAPI `dependency_overrides[authenticate]`
to inject a synthetic `IntegrationAuthContext`.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request

from viberoi_shared.cognito import CognitoClaims, verify_jwt
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
    """Parse + verify the Cognito JWT; build the auth context.

    In Slice 4, `verify_jwt` raises `CognitoNotImplemented`. Tests override
    this dependency via `app.dependency_overrides[authenticate] = ...`.
    """
    token = _parse_bearer(request)
    claims: CognitoClaims = await verify_jwt(token)

    ctx = IntegrationAuthContext(
        developer_id=UUID(claims.sub),
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
