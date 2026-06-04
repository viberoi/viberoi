"""Cognito access-token JWT validation + JWKS cache.

`verify_jwt(token)` returns a typed `CognitoClaims` Pydantic model
with `sub`, `org_id`, `role`, `team_id` custom attributes resolved.
JWKS cached in-process 1h; an unknown `kid` triggers one forced
refresh to handle key rotation.

Slice 5A: real implementation. `CognitoNotImplemented` retained as a
re-export so any caller still importing it gets a clean migration path.
"""

from viberoi_shared.cognito.admin import (
    InviteEmailAlreadyExists,
    InviteError,
    admin_create_invited_user,
    admin_delete_user,
)
from viberoi_shared.cognito.verify import (
    CognitoClaims,
    CognitoNotImplemented,
    CognitoVerificationError,
    reset_jwks_cache,
    verify_jwt,
    verify_jwt_basic,
)

__all__ = [
    "CognitoClaims",
    "CognitoNotImplemented",
    "CognitoVerificationError",
    "InviteEmailAlreadyExists",
    "InviteError",
    "admin_create_invited_user",
    "admin_delete_user",
    "reset_jwks_cache",
    "verify_jwt",
    "verify_jwt_basic",
]
