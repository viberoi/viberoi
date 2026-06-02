"""Per-trigger Lambda authentication.

Every Lambda's first line of logic is:

    from viberoi_shared.lambda_auth import verify
    verify(event, context, expected_source="<source>")

Sources:

  webhook:<provider>          — event must be a valid API Gateway HTTP API v2
                                POST. The actual HMAC check on the body lives
                                in `viberoi_shared.webhooks.verify(...)`;
                                this layer just confirms the invocation
                                shape so a stray invocation of the wrong type
                                fails fast.

  cognito:presignup           — event.userPoolId matches `COGNITO_USER_POOL_ID`
                                env var; event.triggerSource is the expected
                                Cognito event name.

  cognito:postconfirmation    — same idea, different triggerSource.

  eventbridge:<rule>          — event.source == "aws.events" and
                                event.resources contains the rule's ARN.

For webhook providers, the `expected_source` extension `:<provider>` is
echoed back in the bound log context — it's not used to dispatch
verification (HMAC verifies elsewhere).
"""

from __future__ import annotations

import os
from typing import Any

from viberoi_shared.errors import Unauthorized
from viberoi_shared.logging import bind_request_context, get_logger

logger = get_logger(__name__)

# Cognito trigger source names — the exact strings Cognito sends.
_COGNITO_TRIGGER_SOURCES = {
    "cognito:presignup": "PreSignUp_SignUp",
    "cognito:postconfirmation": "PostConfirmation_ConfirmSignUp",
}


def _verify_webhook(event: dict[str, Any]) -> None:
    """API Gateway HTTP API v2 sanity check.

    Doesn't verify the HMAC — that's the caller's responsibility, using
    `viberoi_shared.webhooks.verify(provider, headers, raw_body, secret)`.
    This just confirms the event LOOKS like an API Gateway HTTP API v2
    POST, so a misrouted invocation doesn't get to the body-parsing step.
    """
    if event.get("version") != "2.0":
        raise Unauthorized
    request_ctx = event.get("requestContext") or {}
    http = request_ctx.get("http") or {}
    if http.get("method", "").upper() != "POST":
        raise Unauthorized


def _verify_cognito(event: dict[str, Any], expected_source: str) -> None:
    expected_user_pool = os.environ.get("COGNITO_USER_POOL_ID")
    if not expected_user_pool:
        # Configuration error — log it but fail closed.
        logger.error("cognito_user_pool_id_env_var_missing")
        raise Unauthorized
    if event.get("userPoolId") != expected_user_pool:
        raise Unauthorized
    expected_trigger = _COGNITO_TRIGGER_SOURCES.get(expected_source)
    if expected_trigger is None or event.get("triggerSource") != expected_trigger:
        raise Unauthorized


def _verify_eventbridge(event: dict[str, Any], expected_source: str) -> None:
    if event.get("source") != "aws.events":
        raise Unauthorized
    # expected_source format: "eventbridge:<rule_name>"
    rule_name = expected_source.split(":", 1)[1] if ":" in expected_source else ""
    if not rule_name:
        raise Unauthorized
    resources = event.get("resources") or []
    if not any(rule_name in resource for resource in resources):
        raise Unauthorized


def verify(event: dict[str, Any], context: Any, *, expected_source: str) -> None:  # noqa: ARG001
    """Validate the Lambda invocation source. Raises `Unauthorized` on mismatch.

    `expected_source` patterns:
      - `webhook:github` / `webhook:gitlab` / `webhook:linear`
      - `cognito:presignup` / `cognito:postconfirmation`
      - `eventbridge:<rule_name>`
    """
    aws_request_id = getattr(context, "aws_request_id", None) if context else None
    bind_request_context(request_id=aws_request_id or "lambda")

    source_kind = expected_source.split(":", 1)[0]

    if source_kind == "webhook":
        _verify_webhook(event)
    elif expected_source in ("cognito:presignup", "cognito:postconfirmation"):
        _verify_cognito(event, expected_source)
    elif source_kind == "eventbridge":
        _verify_eventbridge(event, expected_source)
    else:
        raise Unauthorized

    logger.info("lambda_auth_verified", expected_source=expected_source)
