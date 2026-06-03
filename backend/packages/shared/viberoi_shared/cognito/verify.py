"""Cognito access-token JWT verification.

Validates RS256-signed access tokens issued by the configured Cognito
user pool. JWKS is fetched on demand and cached in-process; an unknown
`kid` triggers a single forced refresh in case the pool rotated keys.

Why access tokens, not ID tokens:
- AWS recommends access tokens for backend authorization (ID tokens are
  for the frontend).
- Smaller payload, less PII risk if accidentally logged.
- Custom attributes (`custom:org_id`, `custom:role`, `custom:team_id`)
  reach the access token via the user pool's access-token-customization
  feature (configured in Terraform when the pool is provisioned).

The verifier intentionally does NOT call into Cognito for the user — the
JWT plus JWKS is sufficient. No DB call, no network call beyond JWKS.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

import httpx
import jwt
from jwt import PyJWKClient
from pydantic import BaseModel, ConfigDict, ValidationError

from viberoi_shared.config import get_settings
from viberoi_shared.errors import VibeRoiError
from viberoi_shared.logging import get_logger
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

JWKS_CACHE_TTL_SECONDS = 3600  # 1 hour
JWKS_FETCH_TIMEOUT_SECONDS = 5
EXPECTED_TOKEN_USE = "access"


class CognitoNotImplemented(VibeRoiError):
    """Kept for backwards-compatibility with services that import it."""

    code = "cognito_not_implemented"
    safe_message = "Cognito JWT validation not yet implemented."


class CognitoVerificationError(VibeRoiError):
    code = "cognito_verification_failed"
    safe_message = "Authentication failed."


class CognitoClaims(BaseModel):
    """Parsed Cognito access-token claims after signature verification.

    `developer_id` is the `developers.id` row PK — set by the
    PostConfirmation Lambda as `custom:developer_id` so services don't
    have to look it up on every request. `sub` is Cognito's user
    identifier (distinct).
    """

    model_config = ConfigDict(extra="ignore")

    sub: str  # Cognito user identifier
    developer_id: UUID
    org_id: UUID
    role: Role
    team_id: UUID | None = None
    email: str | None = None  # for diagnostic logging only — never persist


# ── JWKS cache ──────────────────────────────────────────────────────────────


_jwks_client: PyJWKClient | None = None
_jwks_fetched_at: float = 0.0


def _jwks_url() -> str:
    settings = get_settings()
    return (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )


def _issuer() -> str:
    settings = get_settings()
    return (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}"
    )


def _get_jwks_client(*, force_refresh: bool = False) -> PyJWKClient:
    global _jwks_client, _jwks_fetched_at
    now = time.time()
    stale = (now - _jwks_fetched_at) > JWKS_CACHE_TTL_SECONDS
    if _jwks_client is None or stale or force_refresh:
        _jwks_client = PyJWKClient(
            _jwks_url(),
            cache_keys=True,
            timeout=JWKS_FETCH_TIMEOUT_SECONDS,
        )
        _jwks_fetched_at = now
    return _jwks_client


def reset_jwks_cache() -> None:
    """Clear the in-process JWKS cache. Test helper."""
    global _jwks_client, _jwks_fetched_at
    _jwks_client = None
    _jwks_fetched_at = 0.0


# ── verify_jwt ──────────────────────────────────────────────────────────────


async def verify_jwt(token: str) -> CognitoClaims:
    """Verify a Cognito access token and return the typed claims.

    Raises `CognitoVerificationError` on any failure — signature, expiry,
    issuer, client_id, missing custom attrs, etc. Callers MUST treat any
    raise as 401 and not surface the exception message to the user.
    """
    settings = get_settings()
    try:
        signing_key = _resolve_signing_key(token)
        raw = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=_issuer(),
            leeway=settings.cognito_jwt_leeway_s,
            options={"require": ["exp", "iat", "iss", "sub", "token_use"]},
        )
    except jwt.PyJWTError as e:
        # Log the exception class only — PyJWT exception messages can echo
        # claim values; do not surface them to logs.
        logger.warning("cognito_jwt_invalid", error_type=type(e).__name__)
        raise CognitoVerificationError("Invalid Cognito JWT.") from e

    if raw.get("token_use") != EXPECTED_TOKEN_USE:
        logger.warning("cognito_jwt_wrong_token_use", got=raw.get("token_use"))
        raise CognitoVerificationError("Wrong token_use; expected access token.")

    if raw.get("client_id") != settings.cognito_app_client_id:
        logger.warning("cognito_jwt_wrong_client_id")
        raise CognitoVerificationError("Token client_id does not match.")

    return _parse_claims(raw)


def _resolve_signing_key(token: str) -> Any:
    """Fetch the signing key for the token's `kid`. Refreshes JWKS once
    if the `kid` isn't in the cached set (handles key rotation)."""
    try:
        return _get_jwks_client().get_signing_key_from_jwt(token).key
    except jwt.PyJWKClientError:
        # Force-refresh once in case the pool rotated keys after our cache.
        return _get_jwks_client(force_refresh=True).get_signing_key_from_jwt(token).key
    except httpx.HTTPError as e:
        logger.warning("cognito_jwks_fetch_failed", error_type=type(e).__name__)
        raise CognitoVerificationError("Could not fetch JWKS.") from e


def _parse_claims(raw: dict[str, Any]) -> CognitoClaims:
    """Lift Cognito's `custom:*` namespaced attrs into our typed shape."""
    flat: dict[str, Any] = {
        "sub": raw.get("sub"),
        "developer_id": raw.get("custom:developer_id"),
        "org_id": raw.get("custom:org_id"),
        "role": raw.get("custom:role"),
        "team_id": raw.get("custom:team_id") or None,
        "email": raw.get("email"),
    }
    try:
        return CognitoClaims.model_validate(flat)
    except ValidationError as e:
        # Don't log the raw ValidationError — it echoes the missing/invalid
        # field values (which can include claim payload contents).
        logger.warning("cognito_jwt_missing_custom_attrs")
        raise CognitoVerificationError("Missing or invalid custom attributes.") from e
