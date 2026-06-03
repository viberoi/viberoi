"""Seed the dev Postgres + Redis with mock org / developers / sessions.

Runs from the repo root:
    uv run python scripts/seed-dev-data.py

Idempotent — re-running upserts the same fixtures. UUIDs are hardcoded
so the frontend's dev users (in `frontend/src/pages/Login.tsx`) match
real rows.

Loads ~25 sessions across 3 developers with varied attribution + cost,
plus 1 active sprint and 4 tickets, so the dashboard isn't empty.
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from viberoi_shared.crypto import encrypt_pii, hmac_for_lookup
from viberoi_shared.db import org_scoped_session, superuser_session
from viberoi_shared.orgs import (
    create_developer_if_missing,
    create_org_if_missing,
)
from viberoi_shared.tickets import upsert_sprint, upsert_ticket

# Hardcoded IDs — must match `frontend/src/pages/Login.tsx`.
ORG_ID = UUID("00000000-0000-0000-0000-000000000001")
TEAM_ID = UUID("00000000-0000-0000-0000-000000000010")
ADMIN_DEV_ID = UUID("00000000-0000-0000-0000-000000000101")
LEAD_DEV_ID = UUID("00000000-0000-0000-0000-000000000102")
DEVELOPER_DEV_ID = UUID("00000000-0000-0000-0000-000000000103")

SPRINT_ID = UUID("00000000-0000-0000-0000-000000000020")
TICKET_IDS = [
    UUID(f"00000000-0000-0000-0000-0000000003{i:02d}") for i in range(1, 5)
]

DOMAIN = "acme.test"

DEVS = [
    (ADMIN_DEV_ID, "admin@acme.test", "OrgAdmin", "cog-admin-1"),
    (LEAD_DEV_ID, "lead@acme.test", "TeamLead", "cog-lead-1"),
    (DEVELOPER_DEV_ID, "dev@acme.test", "Developer", "cog-dev-1"),
]


async def seed() -> None:
    print("[1/4] Seeding org + developers")
    async with superuser_session() as db:
        org_enc = await encrypt_pii(DOMAIN, context=f"domain:{DOMAIN}:field:name")
        await create_org_if_missing(
            db,
            domain=DOMAIN,
            name_ciphertext=org_enc.ciphertext,
            name_key_version=org_enc.key_version,
            name_iv=org_enc.iv,
        )
        # Force the well-known org_id even if the upsert assigned a new UUID
        # — this matters for first-run when the row didn't already exist.
        await db.execute(
            text(
                "UPDATE orgs SET id = :want WHERE domain = :domain AND id != :want"
            ),
            {"want": str(ORG_ID), "domain": DOMAIN},
        )

        # Ensure a team row exists. Don't pre-set lead_developer_id — we'll
        # update it after the lead developer's row is created (FK CHECK).
        await db.execute(
            text(
                """
                INSERT INTO teams (id, org_id, name)
                VALUES (:id, :org_id, 'Team A')
                ON CONFLICT (id) DO UPDATE SET org_id = EXCLUDED.org_id
                """
            ),
            {"id": str(TEAM_ID), "org_id": str(ORG_ID)},
        )

        for dev_id, email, role, sub in DEVS:
            email_enc = await encrypt_pii(
                email, context=f"org:{ORG_ID}:developer:field:email"
            )
            email_hash = await hmac_for_lookup(email.lower())
            await create_developer_if_missing(
                db,
                org_id=ORG_ID,
                cognito_sub=sub,
                role=role,
                email_ciphertext=email_enc.ciphertext,
                email_key_version=email_enc.key_version,
                email_iv=email_enc.iv,
                email_hash=email_hash,
            )
            # Pin the developer id + team membership for the lead/dev rows.
            await db.execute(
                text(
                    """
                    UPDATE developers
                    SET id = :want,
                        team_id = :team_id
                    WHERE cognito_sub = :sub AND id != :want
                    """
                ),
                {
                    "want": str(dev_id),
                    "team_id": str(TEAM_ID)
                    if dev_id in (LEAD_DEV_ID, DEVELOPER_DEV_ID)
                    else None,
                    "sub": sub,
                },
            )
        # Backfill the team's lead now that the lead row exists.
        await db.execute(
            text(
                "UPDATE teams SET lead_developer_id = :lead WHERE id = :id"
            ),
            {"lead": str(LEAD_DEV_ID), "id": str(TEAM_ID)},
        )

    print("[2/4] Seeding sprint + tickets")
    now = datetime.now(tz=UTC)
    async with org_scoped_session(ORG_ID) as db:
        await upsert_sprint(
            db,
            org_id=ORG_ID,
            system="jira",
            external_id="S42",
            name="Sprint 42",
            state="active",
            started_at=now - timedelta(days=7),
            ended_at=now + timedelta(days=7),
            board_id="B1",
        )
        await db.execute(
            text("UPDATE sprints SET id = :want WHERE org_id = :org AND external_id = 'S42' AND id != :want"),
            {"want": str(SPRINT_ID), "org": str(ORG_ID)},
        )
        for i, tid in enumerate(TICKET_IDS):
            await upsert_ticket(
                db,
                org_id=ORG_ID,
                system="jira",
                external_id=f"ACME-{100 + i}",
                title=f"Demo ticket {i + 1}",
                status="open" if i % 2 == 0 else "in_progress",
                sprint_id=SPRINT_ID,
                story_points=Decimal(random.choice([1, 2, 3, 5])),
                priority="medium",
                created_at_external=now - timedelta(days=5 + i),
            )
            await db.execute(
                text(
                    "UPDATE tickets SET id = :want WHERE org_id = :org AND external_id = :ext AND id != :want"
                ),
                {
                    "want": str(tid),
                    "org": str(ORG_ID),
                    "ext": f"ACME-{100 + i}",
                },
            )

    print("[3/4] Seeding sessions")
    async with org_scoped_session(ORG_ID) as db:
        # Clear any prior seed sessions to avoid accumulation across runs.
        await db.execute(
            text(
                "DELETE FROM sessions WHERE org_id = :org AND session_id LIKE 'seed-%'"
            ),
            {"org": str(ORG_ID)},
        )
        rng = random.Random(1)  # deterministic
        tools = [
            ("claude_code", "claude-opus-4-7", "claude_code", "0.5.0"),
            ("cursor", "claude-sonnet-4-6", "cursor", "0.42"),
            ("copilot", "gpt-4o", "vscode", "1.190"),
        ]
        modes = ["interactive", "agentic", "background"]
        devs = [ADMIN_DEV_ID, LEAD_DEV_ID, DEVELOPER_DEV_ID]

        for i in range(25):
            started = now - timedelta(hours=i * 3, minutes=rng.randint(0, 59))
            ended = started + timedelta(minutes=rng.randint(5, 60))
            tool_name, model, surface, version = rng.choice(tools)
            ticket_ext = rng.choice([None, "ACME-100", "ACME-101", "ACME-102"])
            await db.execute(
                text(
                    """
                    INSERT INTO sessions (
                      session_id, developer_id, org_id,
                      tool_name, tool_surface, tool_version, tool_model, tool_capture_mode,
                      tool_pricing_type, tool_pricing_unit, tool_pricing_rate_usd,
                      started_at, ended_at, active_duration_min,
                      tokens_input, tokens_output, total_cost_usd, is_estimated,
                      turn_count, mode, is_agentic,
                      repo_name, repo_origin_cwd, repo_branch,
                      attr_ticket_id, attr_signals, attr_method,
                      captured_at, agent_version, schema_version
                    ) VALUES (
                      :sid, :dev, :org,
                      :tool, :surface, :ver, :model, 'first_party',
                      'per_token', 'mtok', 15,
                      :started, :ended, :dur,
                      :tin, :tout, :cost, false,
                      :turns, :mode, :agentic,
                      'acme/web', '/repo/acme/web', :branch,
                      :ticket, '{branch_parse}'::text[], 'branch_parse',
                      :captured, :agent_ver, '1.0'
                    )
                    """
                ),
                {
                    "sid": f"seed-{i:03d}",
                    "dev": str(rng.choice(devs)),
                    "org": str(ORG_ID),
                    "tool": tool_name,
                    "surface": surface,
                    "ver": version,
                    "model": model,
                    "started": started,
                    "ended": ended,
                    "dur": int((ended - started).total_seconds() / 60),
                    "tin": rng.randint(2000, 60000),
                    "tout": rng.randint(500, 8000),
                    "cost": Decimal(f"{rng.uniform(0.10, 4.50):.4f}"),
                    "turns": rng.randint(1, 40),
                    "mode": rng.choice(modes),
                    "agentic": rng.random() < 0.4,
                    "branch": f"feature/seed-{i:03d}",
                    "ticket": ticket_ext,
                    "captured": ended,
                    "agent_ver": "0.1.0",
                },
            )

    print("[4/4] Seed complete")


if __name__ == "__main__":
    asyncio.run(seed())
