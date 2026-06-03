"""Cognito PreSignUp Lambda — `cognito_presignup.handler.handler`.

Two checks, in order:
  1. Reject consumer email domains (gmail/yahoo/etc.).
  2. Reject if an org already exists for the email's domain.

Raise → Cognito denies the signup and surfaces the message to the user.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from viberoi_shared.db import superuser_session
from viberoi_shared.errors import Unauthorized
from viberoi_shared.lambda_auth import verify as lambda_auth_verify
from viberoi_shared.logging import bind_request_context, configure_logging, get_logger
from viberoi_shared.orgs import get_org_by_domain

logger = get_logger(__name__)

configure_logging()

# Common consumer email providers — kept tight for V1; the cohort that
# matters is "free webmail provider", not every possible domain. Add
# more via the CONSUMER_EMAIL_DENYLIST env var (comma-separated).
DEFAULT_CONSUMER_DENYLIST = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "ymail.com",
        "rocketmail.com",
        "hotmail.com",
        "outlook.com",
        "live.com",
        "msn.com",
        "icloud.com",
        "me.com",
        "mac.com",
        "aol.com",
        "protonmail.com",
        "proton.me",
        "pm.me",
        "yandex.com",
        "yandex.ru",
        "mail.com",
        "gmx.com",
        "zoho.com",
        "fastmail.com",
        "tutanota.com",
    }
)


class SignupRejected(Exception):
    """Raised → Cognito surfaces the message to the signup form."""


def _consumer_denylist() -> frozenset[str]:
    extra = os.environ.get("CONSUMER_EMAIL_DENYLIST", "")
    extras = {d.strip().lower() for d in extra.split(",") if d.strip()}
    return DEFAULT_CONSUMER_DENYLIST | extras


def _domain_of(email: str) -> str:
    """Extract the email domain and normalize to ASCII lowercase.

    Rejects unicode lookalikes (e.g. fullwidth period U+FF0E,
    ideographic period U+3002) and IDN/punycode variants up-front so an
    attacker can't bypass the consumer denylist with `gmail。com` or
    `xn--gmail-rxa.com`. Trailing dots are stripped (`gmail.com.` =
    `gmail.com`).
    """
    if "@" not in email:
        raise SignupRejected("Please use a valid email address.")
    raw_domain = email.rsplit("@", 1)[1].strip().rstrip(".").lower()
    if not raw_domain or not raw_domain.isascii():
        raise SignupRejected("Please use a valid email address.")
    return raw_domain


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Cognito PreSignUp trigger handler.

    Returns the event back on success (Cognito requires the event echo).
    Raises on rejection — Cognito propagates the message to the SDK
    caller.
    """
    bind_request_context(
        request_id=getattr(context, "aws_request_id", "lambda") if context else "lambda"
    )
    try:
        lambda_auth_verify(event, context, expected_source="cognito:presignup")
    except Unauthorized:
        logger.warning("presignup_lambda_auth_failed")
        raise SignupRejected("Invalid signup request.") from None

    user_attrs = (event.get("request") or {}).get("userAttributes") or {}
    email = (user_attrs.get("email") or "").strip()
    if not email:
        raise SignupRejected("Email address is required.")

    domain = _domain_of(email)

    if domain in _consumer_denylist():
        logger.info("presignup_rejected_consumer_domain", domain=domain)
        raise SignupRejected(
            "Please sign up with your work email address. "
            "Personal email providers are not supported."
        )

    try:
        existing = asyncio.run(_lookup_existing_org(domain))
    except Exception as e:
        # `error_type` only — `str(e)` from asyncpg/SQLAlchemy can echo DSN fragments.
        logger.exception(
            "presignup_org_lookup_failed",
            domain=domain,
            error_type=type(e).__name__,
        )
        # Fail-closed — surface a generic message; don't leak DB state.
        raise SignupRejected(
            "We hit a problem with your signup. Please try again in a minute."
        ) from e

    if existing is not None:
        logger.info("presignup_rejected_existing_org", domain=domain)
        raise SignupRejected(
            "Your team is already on VibeROI. Ask your admin to invite you."
        )

    logger.info("presignup_accepted", domain=domain)
    # Cognito requires the event echo. We do NOT auto-confirm; the
    # user still needs to verify their email (OTP per spec).
    return event


async def _lookup_existing_org(domain: str) -> Any:
    async with superuser_session() as db:
        return await get_org_by_domain(db, domain)
