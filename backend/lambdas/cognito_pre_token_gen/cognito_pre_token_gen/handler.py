"""Cognito Pre Token Generation v2.0 Lambda — `cognito_pre_token_gen.handler.handler`.

Lifts `custom:org_id`, `custom:developer_id`, `custom:role`, and
`custom:team_id` from the user's stored attributes into the *access*
token's claims. ID tokens already contain these by default; access
tokens do not, which is why this Lambda exists.

Slice 5A locked the backend verifier to access tokens (AWS-recommended,
less PII), so the API service depends on this Lambda running to find
the custom claims it needs to build `CognitoClaims`.

Fail-closed contract: if any required attribute is missing, we
return the event unchanged. The backend verifier will reject the
resulting token because `developer_id` / `org_id` / `role` are
required fields on `CognitoClaims`.

NO DB call. NO secret fetch. This runs on every sign-in and refresh;
keep it fast.
"""

from __future__ import annotations

from typing import Any

from viberoi_shared.logging import bind_request_context, configure_logging, get_logger

logger = get_logger(__name__)

configure_logging()

REQUIRED_CLAIMS = ("custom:org_id", "custom:developer_id", "custom:role")
OPTIONAL_CLAIMS = ("custom:team_id",)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Cognito PreTokenGeneration v2 handler.

    Cognito always expects the event echoed back, with `response`
    populated if claim overrides are wanted. Returning the event
    unchanged is the no-op path.
    """
    bind_request_context(
        request_id=getattr(context, "aws_request_id", "lambda") if context else "lambda"
    )

    user_attrs = (event.get("request") or {}).get("userAttributes") or {}

    # Verify required attrs are present. Missing → return event unchanged;
    # the JWT verifier on the backend will reject the resulting token.
    missing = [c for c in REQUIRED_CLAIMS if not user_attrs.get(c)]
    if missing:
        logger.warning("pre_token_gen_missing_required_attrs", count=len(missing))
        return event

    claims_to_add: dict[str, str] = {
        claim: user_attrs[claim] for claim in REQUIRED_CLAIMS
    }
    for claim in OPTIONAL_CLAIMS:
        value = user_attrs.get(claim)
        if value:
            claims_to_add[claim] = value

    # Initialize the response shape if Cognito sent it null.
    response = event.setdefault("response", {})
    response["claimsAndScopeOverrideDetails"] = {
        "accessTokenGeneration": {
            "claimsToAddOrOverride": claims_to_add,
        },
    }

    logger.info(
        "pre_token_gen_claims_injected",
        added_claim_count=len(claims_to_add),
    )
    return event
