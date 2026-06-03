"""GET /developers/me — caller's own profile.

Returns decrypted PII (email, github_username) — but ONLY for the
caller's own row. We never decrypt another developer's PII through
this endpoint.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from api.app.auth import ApiAuthContext, require_role
from api.schema.responses import DeveloperProfile
from viberoi_shared.crypto import decrypt_pii
from viberoi_shared.crypto.envelope import EncryptedField
from viberoi_shared.db import org_scoped_session
from viberoi_shared.logging import get_logger
from viberoi_shared.orgs import get_developer
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()


async def _decrypt_pii_for_self(row, org_id) -> tuple[str, str | None]:
    """Decrypt the developer's own email + github_username (when present).

    AAD contexts MUST match what PostConfirmation / the agent used to
    encrypt — otherwise GCM tag verification fails.
    """
    email = await decrypt_pii(
        EncryptedField(
            ciphertext=row.email_ciphertext,
            key_version=row.email_key_version,
            iv=row.email_iv,
        ),
        context=f"org:{org_id}:developer:field:email",
    )
    github_username: str | None = None
    if row.github_username_ciphertext is not None:
        github_username = await decrypt_pii(
            EncryptedField(
                ciphertext=row.github_username_ciphertext,
                key_version=row.github_username_key_version or 1,
                iv=row.github_username_iv or b"",
            ),
            context=f"org:{org_id}:developer:field:github_username",
        )
    return email, github_username


@router.get("/me", response_model=DeveloperProfile)
async def me_route(
    ctx: Annotated[
        ApiAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
) -> DeveloperProfile:
    async with org_scoped_session(ctx.org_id) as db:
        row = await get_developer(db, ctx.developer_id)
    email, github_username = await _decrypt_pii_for_self(row, ctx.org_id)
    return DeveloperProfile(
        id=row.id,
        org_id=row.org_id,
        role=row.role,
        team_id=row.team_id,
        email=email,
        github_username=github_username,
        agent_status=row.agent_status,
        created_at=row.created_at,
        last_active_at=row.last_active_at,
    )
