"""Create a local org + developer row for a user who already exists in Cognito.

Replaces the PostConfirmation Lambda for early dev. After someone signs up
via the Hosted UI, run this once to give them a record in the local DB so
API calls authenticate.

Domain-uniqueness: if the email's domain already has an org, the new
developer attaches to that org as `Developer`. If not, a new org is
created and the user becomes `OrgAdmin`.

Usage:
    uv run python scripts/bootstrap-cognito-user.py \\
        --email alice@acme.com \\
        --sub <cognito-sub-from-hosted-ui-or-aws-console>

The Cognito sub is the user's permanent ID — find it under "Users" in
the AWS Cognito console, or run:
    aws cognito-idp admin-get-user \\
        --user-pool-id us-east-1_CuEMR2XEY \\
        --username <email>
"""

from __future__ import annotations

import argparse
import asyncio
from uuid import uuid4

from sqlalchemy import text

from viberoi_shared.crypto import encrypt_pii, hmac_for_lookup
from viberoi_shared.db import superuser_session
from viberoi_shared.types.enums import Role

CONSUMER_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "live.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
}


async def bootstrap(email: str, cognito_sub: str) -> None:
    email = email.strip().lower()
    if "@" not in email:
        raise SystemExit(f"invalid email: {email}")
    domain = email.rsplit("@", 1)[1]
    if domain in CONSUMER_DOMAINS:
        print(
            f"warn: '{domain}' is a consumer email domain. The PreSignUp "
            f"Lambda will reject this when deployed. Proceeding anyway "
            f"for early dev."
        )

    async with superuser_session() as db:
        existing = (
            await db.execute(
                text("SELECT id FROM developers WHERE cognito_sub = :sub"),
                {"sub": cognito_sub},
            )
        ).first()
        if existing:
            print(f"developer already exists: {existing[0]}")
            return

        org_row = (
            await db.execute(
                text("SELECT id FROM orgs WHERE domain = :d"),
                {"d": domain},
            )
        ).first()

        if org_row is None:
            org_id = uuid4()
            domain_enc = await encrypt_pii(
                domain, context=f"domain:{domain}:field:name"
            )
            await db.execute(
                text(
                    """
                    INSERT INTO orgs
                        (id, domain, name_ciphertext,
                         name_key_version, name_iv)
                    VALUES (:id, :d, :ct, :kv, :iv)
                    """
                ),
                {
                    "id": str(org_id),
                    "d": domain,
                    "ct": domain_enc.ciphertext,
                    "kv": domain_enc.key_version,
                    "iv": domain_enc.iv,
                },
            )
            role = Role.ORG_ADMIN
            print(f"created org: {org_id} ({domain}) — first user, OrgAdmin")
        else:
            org_id = org_row[0]
            role = Role.DEVELOPER
            print(f"attached to existing org: {org_id} ({domain}) — Developer")

        dev_id = uuid4()
        email_enc = await encrypt_pii(
            email, context=f"org:{org_id}:developer:field:email"
        )
        email_hash = await hmac_for_lookup(email)
        await db.execute(
            text(
                """
                INSERT INTO developers
                    (id, org_id, cognito_sub, role,
                     email_ciphertext, email_key_version, email_iv, email_hash)
                VALUES (:id, :org, :sub, :role, :ct, :kv, :iv, :hash)
                """
            ),
            {
                "id": str(dev_id),
                "org": str(org_id),
                "sub": cognito_sub,
                "role": role.value,
                "ct": email_enc.ciphertext,
                "kv": email_enc.key_version,
                "iv": email_enc.iv,
                "hash": email_hash,
            },
        )
        print(f"created developer: {dev_id}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True)
    p.add_argument("--sub", required=True, help="Cognito user sub (UUID)")
    args = p.parse_args()
    asyncio.run(bootstrap(args.email, args.sub))


if __name__ == "__main__":
    main()
