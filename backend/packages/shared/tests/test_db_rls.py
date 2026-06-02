"""DB Row-Level Security — integration test.

Proves Postgres RLS actually isolates tenants even when app code omits
the org_id filter. Without this guarantee, the whole tenant-isolation
story collapses to "we hope app code is correct."

Requires Postgres from docker-compose (and the viberoi_admin role
provisioned by scripts/postgres-init.sql).
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from viberoi_shared.db import org_scoped_session, superuser_session
from viberoi_shared.orgs.models import Developer, Org, OrgToken
from viberoi_shared.sessions import upsert
from viberoi_shared.sessions.models import SessionRow
from viberoi_shared.types import (
    Activity,
    Attribution,
    CodeOutput,
    Meta,
    Pricing,
    Quality,
    Repository,
    Session,
    Timing,
    Tokens,
    ToolInfo,
)
from viberoi_shared.types.enums import (
    CaptureMode,
    HallucinationRisk,
    PricingType,
    PricingUnit,
    SessionMode,
    Surface,
    Tool,
)

pytestmark = pytest.mark.integration


def _build_session(*, org_id: str, developer_id: str, session_id: str) -> Session:
    now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=UTC)
    return Session(
        session_id=session_id,
        developer_id=developer_id,
        org_id=org_id,
        tool=ToolInfo(
            name=Tool.CLAUDE_CODE,
            surface=Surface.DESKTOP_APP,
            version="1.0",
            model="claude-sonnet-4-6",
            capture_mode=CaptureMode.LOCAL_EXACT,
            pricing_model=Pricing(
                type=PricingType.SUBSCRIPTION, unit=PricingUnit.TOKENS, rate_usd=0
            ),
        ),
        timing=Timing(started_at=now, ended_at=now, active_duration_min=1),
        tokens=Tokens(input=1, output=1, total_cost_usd=0, is_estimated=False),
        activity=Activity(turn_count=1, mode=SessionMode.AGENT, is_agentic=True),
        code_output=CodeOutput(),
        repository=Repository(name="r", origin_cwd="/r", branch="main"),
        attribution=Attribution(),
        quality=Quality(hallucination_risk=HallucinationRisk.NONE),
        meta=Meta(captured_at=now, agent_version="0.1.0"),
    )


@pytest.fixture
async def two_orgs_with_data() -> tuple[Org, Org, Developer, Developer]:
    """Create two orgs, each with a developer + token + session row.

    Cleanup runs after the test via SQL DELETE (the BYPASSRLS admin can
    delete across orgs).
    """
    org_a_id = uuid4()
    org_b_id = uuid4()
    dev_a_id = uuid4()
    dev_b_id = uuid4()

    async with superuser_session() as db:
        # Two orgs
        org_a = Org(
            id=org_a_id,
            domain=f"a-{uuid4().hex[:8]}.test",
            name_ciphertext=b"\x00\x00\x00\x04fake",
            name_key_version=1,
            name_iv=b"\x00" * 12,
        )
        org_b = Org(
            id=org_b_id,
            domain=f"b-{uuid4().hex[:8]}.test",
            name_ciphertext=b"\x00\x00\x00\x04fake",
            name_key_version=1,
            name_iv=b"\x00" * 12,
        )
        db.add(org_a)
        db.add(org_b)
        await db.flush()

        # Two developers
        dev_a = Developer(
            id=dev_a_id,
            org_id=org_a_id,
            cognito_sub=f"cog-a-{uuid4()}",
            email_ciphertext=b"\x00\x00\x00\x04fake",
            email_key_version=1,
            email_iv=b"\x00" * 12,
            email_hash=uuid4().bytes,
        )
        dev_b = Developer(
            id=dev_b_id,
            org_id=org_b_id,
            cognito_sub=f"cog-b-{uuid4()}",
            email_ciphertext=b"\x00\x00\x00\x04fake",
            email_key_version=1,
            email_iv=b"\x00" * 12,
            email_hash=uuid4().bytes,
        )
        db.add(dev_a)
        db.add(dev_b)
        await db.flush()

    # One session per org via org_scoped_session (proves the happy path)
    sess_a = _build_session(
        org_id=str(org_a_id), developer_id=str(dev_a_id), session_id="sess-a-1"
    )
    sess_b = _build_session(
        org_id=str(org_b_id), developer_id=str(dev_b_id), session_id="sess-b-1"
    )
    async with org_scoped_session(org_a_id) as db:
        await upsert(db, sess_a, developer_uuid=dev_a_id, org_uuid=org_a_id)
    async with org_scoped_session(org_b_id) as db:
        await upsert(db, sess_b, developer_uuid=dev_b_id, org_uuid=org_b_id)

    yield (org_a, org_b, dev_a, dev_b)

    # Cleanup — cascade from orgs handles teams/developers/tokens/sessions
    async with superuser_session() as db:
        await db.execute(
            text("DELETE FROM orgs WHERE id IN (:a, :b)"),
            {"a": str(org_a_id), "b": str(org_b_id)},
        )


async def test_org_scoped_session_only_sees_own_sessions(
    two_orgs_with_data: tuple[Org, Org, Developer, Developer],
) -> None:
    """SELECT FROM sessions inside org A's context returns only A's rows."""
    org_a, org_b, _, _ = two_orgs_with_data

    async with org_scoped_session(org_a.id) as db:
        result = await db.execute(select(SessionRow))
        rows = list(result.scalars().all())

    assert len(rows) == 1
    assert rows[0].org_id == org_a.id


async def test_org_scoped_session_b_only_sees_own_data(
    two_orgs_with_data: tuple[Org, Org, Developer, Developer],
) -> None:
    """Symmetric check from org B's side."""
    _, org_b, _, _ = two_orgs_with_data

    async with org_scoped_session(org_b.id) as db:
        result = await db.execute(select(SessionRow))
        rows = list(result.scalars().all())

    assert len(rows) == 1
    assert rows[0].org_id == org_b.id


async def test_org_scoped_session_cannot_insert_for_different_org(
    two_orgs_with_data: tuple[Org, Org, Developer, Developer],
) -> None:
    """RLS WITH CHECK clause should reject inserts whose org_id != GUC."""
    org_a, org_b, _, dev_b = two_orgs_with_data

    rogue = _build_session(
        org_id=str(org_b.id), developer_id=str(dev_b.id), session_id="rogue-sess"
    )

    with pytest.raises(Exception):  # noqa: B017, PT011 — Postgres RLS error
        async with org_scoped_session(org_a.id) as db:
            await upsert(db, rogue, developer_uuid=dev_b.id, org_uuid=org_b.id)


async def test_superuser_session_sees_everything(
    two_orgs_with_data: tuple[Org, Org, Developer, Developer],
) -> None:
    """The admin role (BYPASSRLS) sees both orgs' sessions."""
    async with superuser_session() as db:
        result = await db.execute(
            text("SELECT count(*) FROM sessions WHERE session_id IN ('sess-a-1','sess-b-1')")
        )
        count = result.scalar_one()

    assert count == 2
