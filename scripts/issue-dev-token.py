"""Issue an agent token for a seeded developer (dev only).

Generates a random token, Argon2id-hashes it, inserts an `org_tokens`
row for the developer, and prints the plaintext token to stdout so the
agent can register with it.

Usage:
    uv run python scripts/issue-dev-token.py [--developer-id <uuid>]

Defaults to the OrgAdmin developer the seed script creates.
"""

from __future__ import annotations

import argparse
import asyncio
import secrets
from uuid import UUID

from sqlalchemy import text

from viberoi_shared.crypto import hash_secret
from viberoi_shared.db import superuser_session

DEFAULT_ORG_ID = UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_DEV_ID = UUID("00000000-0000-0000-0000-000000000101")


async def issue(org_id: UUID, dev_id: UUID) -> str:
    plaintext = "viberoi_" + secrets.token_urlsafe(32)
    hashed = hash_secret(plaintext)
    async with superuser_session() as db:
        # Revoke any prior dev-mode tokens for this developer so we don't
        # accumulate them across reruns.
        await db.execute(
            text(
                "UPDATE org_tokens SET revoked_at = now() "
                "WHERE developer_id = :dev AND device_label = 'dev-script' "
                "AND revoked_at IS NULL"
            ),
            {"dev": str(dev_id)},
        )
        await db.execute(
            text(
                """
                INSERT INTO org_tokens (org_id, developer_id, hashed, device_label)
                VALUES (:org, :dev, :hashed, 'dev-script')
                """
            ),
            {"org": str(org_id), "dev": str(dev_id), "hashed": hashed},
        )
    return plaintext


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org-id", default=str(DEFAULT_ORG_ID))
    parser.add_argument("--developer-id", default=str(DEFAULT_DEV_ID))
    args = parser.parse_args()
    token = asyncio.run(issue(UUID(args.org_id), UUID(args.developer_id)))
    print("org_id:      ", args.org_id)
    print("developer_id:", args.developer_id)
    print("token:       ", token)


if __name__ == "__main__":
    main()
