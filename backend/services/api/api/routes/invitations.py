"""Team invite flow — OrgAdmin invites a teammate by email.

Calls Cognito `admin_create_user` (Cognito sends the standard "you've
been invited" email with a temp password), then writes a `developers`
row tied to the returned Cognito `sub` so the invitee lands in the
caller's org with role=Developer the moment they sign in.

Two consistency notes:
  - Cognito + DB are separate systems. We try a best-effort
    `admin_delete_user` rollback if the DB insert fails. A residual
    Cognito user can be cleaned up manually.
  - The email domain MUST match the caller's org domain. Cross-org
    invites would break the "one org per domain" rule.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from pydantic import BaseModel, ConfigDict, EmailStr

from api.app.auth import ApiAuthContext, require_role
from viberoi_shared.cognito import (
    InviteEmailAlreadyExists,
    admin_create_invited_user,
    admin_delete_user,
)
from viberoi_shared.crypto import encrypt_pii, hmac_for_lookup
from viberoi_shared.db import org_scoped_session
from viberoi_shared.errors import Conflict, NotFound, ValidationFailed
from viberoi_shared.logging import get_logger
from viberoi_shared.orgs import (
    create_developer_if_missing,
    get_developer_by_email_hash,
    get_org,
)
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()


class InviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class InviteResponse(BaseModel):
    developer_id: str
    email: str
    role: str
    cognito_sub: str
    message: str


@router.post(
    "",
    response_model=InviteResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def invite_route(
    body: InviteRequest,
    ctx: Annotated[ApiAuthContext, Depends(require_role(Role.ORG_ADMIN))],
) -> InviteResponse:
    email = body.email.lower()
    domain = email.rsplit("@", 1)[1]

    # 1. Enforce same-domain invite (one org per domain rule).
    async with org_scoped_session(ctx.org_id) as db:
        org = await get_org(db, ctx.org_id)
        if org.domain != domain:
            raise ValidationFailed(
                f"Invite email domain '{domain}' does not match your org "
                f"domain '{org.domain}'. Cross-domain invites aren't allowed."
            )

        # 2. Check no developer already exists with that email in this org.
        email_hash = await hmac_for_lookup(email)
        existing = await get_developer_by_email_hash(
            db, org_uuid=ctx.org_id, email_hash=email_hash
        )
        if existing is not None:
            raise Conflict(
                f"A developer with this email already exists in your org."
            )

    # 3. Call Cognito admin_create_user (outside the DB transaction —
    # this is the slow + side-effectful step).
    try:
        cognito_sub = await admin_create_invited_user(email)
    except InviteEmailAlreadyExists:
        raise Conflict(
            "This email is already registered in Cognito. If they belong "
            "to your org, ask them to sign in directly."
        ) from None

    # 4. Insert developer row tied to the new sub. Roll back the Cognito
    # user if the DB write fails.
    try:
        email_enc = await encrypt_pii(
            email, context=f"org:{ctx.org_id}:developer:field:email"
        )
        async with org_scoped_session(ctx.org_id) as db:
            dev = await create_developer_if_missing(
                db,
                org_id=ctx.org_id,
                cognito_sub=cognito_sub,
                role=Role.DEVELOPER.value,
                email_ciphertext=email_enc.ciphertext,
                email_key_version=email_enc.key_version,
                email_iv=email_enc.iv,
                email_hash=email_hash,
            )
    except Exception as e:
        logger.warning(
            "invite_db_insert_failed_rolling_back_cognito",
            error_type=type(e).__name__,
        )
        # Best-effort — if this also fails, surface a clearer error so the
        # operator knows to clean up manually.
        try:
            await admin_delete_user(cognito_sub)
        except Exception:  # noqa: BLE001, S110
            logger.error(
                "invite_cognito_rollback_failed",
                cognito_sub=cognito_sub[:8],
            )
        raise

    logger.info(
        "invite_sent",
        org_id=str(ctx.org_id),
        invited_by=str(ctx.developer_id),
        new_developer_id=str(dev.id),
    )
    return InviteResponse(
        developer_id=str(dev.id),
        email=email,
        role=Role.DEVELOPER.value,
        cognito_sub=cognito_sub,
        message=(
            "Invitation sent — Cognito emailed a temporary password. "
            "The user signs in via the Hosted UI, sets a new password, "
            "and lands in your org as a Developer."
        ),
    )
