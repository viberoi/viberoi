"""Cognito PostConfirmation Lambda — `cognito_postconfirm.handler.handler`.

Creates the `orgs` row (if first user for the domain) and the
`developers` row, then writes `custom:org_id` / `custom:role`
back to Cognito so subsequent access tokens carry them.

Cognito does NOT guarantee exactly-once delivery — every step is
idempotent.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from viberoi_shared.aws import cognito_idp_client
from viberoi_shared.crypto import encrypt_pii, hmac_for_lookup
from viberoi_shared.db import superuser_session
from viberoi_shared.errors import Unauthorized
from viberoi_shared.lambda_auth import verify as lambda_auth_verify
from viberoi_shared.logging import bind_request_context, configure_logging, get_logger
from viberoi_shared.orgs import (
    count_developers,
    create_developer_if_missing,
    create_org_if_missing,
    get_developer_by_cognito_sub,
    lock_org_for_update,
)

logger = get_logger(__name__)

configure_logging()

ROLE_FIRST_USER = "OrgAdmin"
ROLE_INVITED = "Developer"


class PostConfirmationError(Exception):
    """Raised → Cognito treats the user as confirmed but logs the failure.

    PostConfirmation runs AFTER the user is already confirmed; throwing
    here does not roll the user back. We surface failures via CloudWatch
    + DLQ rather than user-facing errors.
    """


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    bind_request_context(
        request_id=getattr(context, "aws_request_id", "lambda") if context else "lambda"
    )
    try:
        lambda_auth_verify(event, context, expected_source="cognito:postconfirmation")
    except Unauthorized:
        logger.warning("postconfirm_lambda_auth_failed")
        raise PostConfirmationError("Invalid invocation source.") from None

    user_attrs = (event.get("request") or {}).get("userAttributes") or {}
    email = (user_attrs.get("email") or "").strip()
    email_verified = str(user_attrs.get("email_verified") or "").lower() == "true"
    cognito_sub = user_attrs.get("sub") or event.get("userName")
    user_pool_id = event.get("userPoolId")
    username = event.get("userName")

    if not email or not cognito_sub or not user_pool_id or not username:
        logger.error("postconfirm_event_missing_required_fields")
        raise PostConfirmationError("Event missing required fields.")

    if not email_verified:
        # Defense-in-depth against a federated IdP (or misconfigured flow)
        # injecting an unverified email. Without this, an attacker could
        # bind an arbitrary `victim@target.com` to their account and become
        # OrgAdmin of the victim's org.
        logger.warning(
            "postconfirm_rejecting_unverified_email",
            cognito_sub=cognito_sub,
        )
        raise PostConfirmationError("Email address has not been verified.")

    domain = email.rsplit("@", 1)[-1].strip().rstrip(".").lower()
    if not domain or not domain.isascii():
        logger.warning("postconfirm_rejecting_unicode_domain")
        raise PostConfirmationError("Invalid email domain.")

    try:
        asyncio.run(
            _provision(
                email=email,
                domain=domain,
                cognito_sub=cognito_sub,
                user_pool_id=user_pool_id,
                username=username,
            )
        )
    except Exception as e:
        # `error_type` only — `str(e)` from asyncpg/SQLAlchemy can echo DSN fragments.
        logger.exception(
            "postconfirm_provisioning_failed",
            domain=domain,
            error_type=type(e).__name__,
        )
        raise PostConfirmationError("Provisioning failed.") from e

    return event


async def _provision(
    *,
    email: str,
    domain: str,
    cognito_sub: str,
    user_pool_id: str,
    username: str,
) -> None:
    # Step 1: idempotency check — if the developer already exists, this
    # invocation is a Cognito retry. Skip provisioning, just sync attrs.
    async with superuser_session() as db:
        existing = await get_developer_by_cognito_sub(db, cognito_sub)
        if existing is not None:
            logger.info(
                "postconfirm_already_provisioned",
                cognito_sub=cognito_sub,
                org_id=str(existing.org_id),
                role=existing.role,
            )
            await _set_cognito_custom_attrs(
                user_pool_id=user_pool_id,
                username=username,
                developer_id=str(existing.id),
                org_id=str(existing.org_id),
                role=existing.role,
            )
            return

    # Step 2: encrypt PII (separate context strings for org-name vs email)
    org_aad = f"domain:{domain}:field:name"
    org_name = await encrypt_pii(domain, context=org_aad)

    # Step 3: org + developer create inside a single session.
    async with superuser_session() as db:
        org = await create_org_if_missing(
            db,
            domain=domain,
            name_ciphertext=org_name.ciphertext,
            name_key_version=org_name.key_version,
            name_iv=org_name.iv,
        )
        # Lock the org row for the role-assignment decision. Without this
        # lock, two concurrent first-user signups can both see
        # `count_developers == 0` and both end up as OrgAdmin.
        await lock_org_for_update(db, org.id)
        existing_count = await count_developers(db, org.id)
        role = ROLE_FIRST_USER if existing_count == 0 else ROLE_INVITED

        email_enc = await encrypt_pii(
            email,
            context=f"org:{org.id}:developer:field:email",
        )
        email_hash = await hmac_for_lookup(email.lower())

        developer = await create_developer_if_missing(
            db,
            org_id=org.id,
            cognito_sub=cognito_sub,
            role=role,
            email_ciphertext=email_enc.ciphertext,
            email_key_version=email_enc.key_version,
            email_iv=email_enc.iv,
            email_hash=email_hash,
        )

    logger.info(
        "postconfirm_provisioned",
        domain=domain,
        org_id=str(org.id),
        developer_id=str(developer.id),
        role=role,
    )

    await _set_cognito_custom_attrs(
        user_pool_id=user_pool_id,
        username=username,
        developer_id=str(developer.id),
        org_id=str(org.id),
        role=role,
    )


async def _set_cognito_custom_attrs(
    *,
    user_pool_id: str,
    username: str,
    developer_id: str,
    org_id: str,
    role: str,
) -> None:
    """Idempotent — Cognito accepts repeated AdminUpdateUserAttributes calls."""
    if os.environ.get("VIBEROI_COGNITO_SKIP_ATTR_WRITE") == "1":
        logger.info(
            "postconfirm_cognito_attrs_skipped_for_test",
            org_id=org_id,
            role=role,
        )
        return
    async with cognito_idp_client() as client:
        await client.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "custom:developer_id", "Value": developer_id},
                {"Name": "custom:org_id", "Value": org_id},
                {"Name": "custom:role", "Value": role},
            ],
        )
    logger.info(
        "postconfirm_cognito_attrs_set",
        developer_id=developer_id,
        org_id=org_id,
        role=role,
    )
