"""Cognito JWT validation + JWKS cache.

`verify_jwt(token)` returns a typed `CognitoClaims` Pydantic model
with `sub`, `org_id`, `role`, `team_id` custom attributes resolved.
JWKS cached in-process 1h; cache miss triggers refresh.

Slice 4 contract: `CognitoClaims` shape locked; `verify_jwt` is a stub
that raises `CognitoNotImplemented`. Services use dependency_overrides
in tests; production wiring lands with Slice 5.
"""

from viberoi_shared.cognito.verify import (
    CognitoClaims,
    CognitoNotImplemented,
    verify_jwt,
)

__all__ = ["CognitoClaims", "CognitoNotImplemented", "verify_jwt"]
