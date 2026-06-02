"""Cognito JWT validation — STUB implementation.

The full implementation (JWKS fetch + cache, signature verify, aud/iss/exp
checks, custom-attribute extraction) lands in Slice 5 alongside the
Cognito user pool Terraform module.

For now this module:
  - Defines the `CognitoClaims` Pydantic shape so services can type their
    code against it.
  - Raises `NotImplementedError` from `verify_jwt` to make the missing
    capability loud at startup (services log it but tests don't hit it
    because they use FastAPI dependency_overrides to inject a fake
    `IntegrationAuthContext` directly).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from viberoi_shared.errors import VibeRoiError
from viberoi_shared.types.enums import Role


class CognitoNotImplemented(VibeRoiError):
    code = "cognito_not_implemented"
    safe_message = "Cognito JWT validation not yet implemented."


class CognitoClaims(BaseModel):
    """Parsed Cognito ID/access-token claims after signature verification.

    `org_id`, `role`, and `team_id` are custom Cognito user attributes set
    by the PostConfirmation Lambda. `sub` is the Cognito user UUID.
    """

    model_config = ConfigDict(extra="ignore")

    sub: str  # Cognito user identifier
    org_id: UUID
    role: Role
    team_id: UUID | None = None
    email: str | None = None  # for diagnostic logging only — never persist


async def verify_jwt(token: str) -> CognitoClaims:  # noqa: ARG001
    """Validate a Cognito JWT and return the claims.

    Slice 5 will:
      - Fetch JWKS from `https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json`
      - Cache JWKS in-process for 1 hour, refresh on cache miss
      - Verify RS256 signature, `iss`, `aud`, `exp`
      - Parse `custom:org_id` / `custom:role` / `custom:team_id` attributes
      - Return `CognitoClaims`
    """
    raise CognitoNotImplemented(
        "Cognito JWT verification lands in Slice 5. "
        "Services in development must use FastAPI dependency_overrides to "
        "inject a synthetic auth context."
    )
