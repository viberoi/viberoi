"""Cognito JWT validation + JWKS cache.

`verify_jwt(token)` returns a typed `CognitoClaims` Pydantic model
with `sub`, `org_id`, `role`, `team_id` custom attributes resolved.
JWKS cached in-process 1h; cache miss triggers refresh.
"""
