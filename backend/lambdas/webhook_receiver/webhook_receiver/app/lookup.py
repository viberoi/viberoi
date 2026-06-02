"""Look up the org_id + decrypted webhook secret for an inbound webhook.

The lookup uses the `superuser_session` (BYPASSRLS) because we don't know
the org until AFTER the lookup succeeds. There's no way around that:
the Lambda has only the path's integration_id at this point.
"""

from __future__ import annotations

from uuid import UUID

from viberoi_shared.crypto import decrypt_pii
from viberoi_shared.crypto.envelope import EncryptedField
from viberoi_shared.db import superuser_session
from viberoi_shared.integrations.models import IntegrationOAuthToken
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)


async def get_webhook_credentials(
    integration_id: UUID, provider: str
) -> tuple[UUID, bytes] | None:
    """Resolve `(org_id, secret_bytes)` or return None.

    Returns None when:
      - integration_id isn't in the table
      - the row is revoked
      - the row's provider doesn't match the path's provider (defense
        in depth against someone POSTing a GitHub-shaped payload to a
        Linear integration URL)
      - the row has no webhook secret stored
    """
    async with superuser_session() as db:
        row = await db.get(IntegrationOAuthToken, integration_id)
        if row is None:
            return None
        if row.revoked_at is not None:
            return None
        if row.provider != provider:
            logger.warning(
                "webhook_provider_mismatch",
                integration_id=str(integration_id),
                expected=row.provider,
                received=provider,
            )
            return None
        if row.webhook_secret_ciphertext is None:
            return None

        plaintext = await decrypt_pii(
            EncryptedField(
                ciphertext=row.webhook_secret_ciphertext,
                key_version=row.webhook_secret_key_version or 1,
                iv=row.webhook_secret_iv or b"",
            ),
            context=(
                f"org:{row.org_id}:integration:{provider}:field:webhook_secret"
            ),
        )
        return (row.org_id, plaintext.encode("utf-8"))
