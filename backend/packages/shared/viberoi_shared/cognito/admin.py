"""Cognito admin operations — invite + revoke.

`admin_create_invited_user(email)` triggers Cognito's standard "you've
been invited" email with a temp password the user must change on first
sign-in. Returns the Cognito `sub` so the caller can wire up a local
developer row in the same transaction (logically — the DB write is in
a separate session).

Why temp-password invite vs self-signup with a token:
- Cognito Hosted UI doesn't let us pass arbitrary state through signup,
  so we can't securely attach a "this user belongs to org X" claim.
- Admin-create gives us the sub up front and lets Cognito handle the
  email + password reset flow for free.
"""

from __future__ import annotations

import secrets
import string

from viberoi_shared.aws import cognito_idp_client
from viberoi_shared.config import get_settings
from viberoi_shared.errors import VibeRoiError
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)


class InviteError(VibeRoiError):
    code = "invite_failed"
    safe_message = "Failed to create invitation."


class InviteEmailAlreadyExists(VibeRoiError):
    code = "invite_email_exists"
    safe_message = "An invitation for this email is already pending."


def _generate_temp_password() -> str:
    """16-char password meeting our pool's policy:
    12+ chars, upper, lower, number, symbol."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(16))
        if (
            any(c.isupper() for c in pw)
            and any(c.islower() for c in pw)
            and any(c.isdigit() for c in pw)
            and any(c in "!@#$%^&*" for c in pw)
        ):
            return pw


async def admin_create_invited_user(email: str) -> str:
    """Create a user in the configured Cognito pool with a temp password.

    Cognito sends the invitation email (subject + body configurable on
    the pool's MessageTemplate; uses Cognito defaults for now). The
    user signs in with the temp password, Cognito forces a reset, and
    they're done.

    Returns the Cognito `sub` (UUID string).
    """
    settings = get_settings()
    pool_id = settings.cognito_user_pool_id
    if not pool_id:
        raise InviteError("cognito_user_pool_id not configured.")

    async with cognito_idp_client() as cognito:
        try:
            resp = await cognito.admin_create_user(
                UserPoolId=pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                ],
                TemporaryPassword=_generate_temp_password(),
                DesiredDeliveryMediums=["EMAIL"],
                # MessageAction omitted → Cognito sends the default
                # "you've been invited" email with the temp password.
            )
        except cognito.exceptions.UsernameExistsException as e:
            raise InviteEmailAlreadyExists from e
        except Exception as e:  # noqa: BLE001
            logger.warning("admin_create_user_failed", error_type=type(e).__name__)
            raise InviteError("Cognito admin_create_user failed.") from e

    user = resp["User"]
    sub = next(
        attr["Value"] for attr in user["Attributes"] if attr["Name"] == "sub"
    )
    logger.info("invite_created", email_domain=email.rsplit("@", 1)[1])
    return sub


async def admin_delete_user(cognito_sub: str) -> None:
    """Remove a user from the Cognito pool. Idempotent — missing user is
    treated as success (the caller wanted them gone; they are)."""
    settings = get_settings()
    pool_id = settings.cognito_user_pool_id
    if not pool_id:
        raise InviteError("cognito_user_pool_id not configured.")

    async with cognito_idp_client() as cognito:
        try:
            # admin_delete_user takes Username, which for our pool is the
            # email. We can also look up by sub via list_users + filter.
            users = await cognito.list_users(
                UserPoolId=pool_id, Filter=f'sub = "{cognito_sub}"', Limit=1
            )
            if not users.get("Users"):
                return  # already gone
            username = users["Users"][0]["Username"]
            await cognito.admin_delete_user(
                UserPoolId=pool_id, Username=username
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("admin_delete_user_failed", error_type=type(e).__name__)
            raise InviteError("Cognito admin_delete_user failed.") from e
