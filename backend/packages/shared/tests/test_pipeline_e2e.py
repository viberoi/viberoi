"""End-to-end pipeline test — integration (LocalStack + Postgres + Redis).

Validates the shared-library data path that Ingest + Worker depend on:

  put_raw_session (S3)
    → get_raw_session
    → Session validation
    → sessions.upsert (Postgres with RLS)
    → redis counter increments

This is the "shared lib end-to-end" test. The actual Ingest service
and Worker service have their own service-level tests; this one
proves the shared helpers compose correctly.
"""

import gzip
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import orjson
import pytest
from sqlalchemy import text

from viberoi_shared.db import org_scoped_session, superuser_session
from viberoi_shared.orgs.models import Developer, Org
from viberoi_shared.redis import (
    get_today_summary,
    incr_cost_usd,
    incr_session_count,
    reset_org_counters,
)
from viberoi_shared.s3 import get_raw_session, put_raw_session
from viberoi_shared.sessions import get_by_external_id, upsert
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


def _build_session(
    *,
    org_id: str,
    developer_id: str,
    session_id: str,
    branch: str = "feature/JIRA-142-test",
    cost: float = 0.42,
) -> Session:
    now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=UTC)
    return Session(
        session_id=session_id,
        developer_id=developer_id,
        org_id=org_id,
        tool=ToolInfo(
            name=Tool.CLAUDE_CODE,
            surface=Surface.DESKTOP_APP,
            version="2.1.128",
            model="claude-sonnet-4-6",
            capture_mode=CaptureMode.LOCAL_EXACT,
            pricing_model=Pricing(
                type=PricingType.SUBSCRIPTION, unit=PricingUnit.TOKENS, rate_usd=0
            ),
        ),
        timing=Timing(started_at=now, ended_at=now, active_duration_min=74),
        tokens=Tokens(
            input=3, output=226, total_cost_usd=Decimal(str(cost)), is_estimated=False
        ),
        activity=Activity(turn_count=4, mode=SessionMode.AGENT, is_agentic=True),
        code_output=CodeOutput(),
        repository=Repository(name="repo", origin_cwd="/r", branch=branch),
        attribution=Attribution(),
        quality=Quality(hallucination_risk=HallucinationRisk.NONE),
        meta=Meta(captured_at=now, agent_version="0.1.0"),
    )


@pytest.fixture
async def org_and_dev() -> tuple[Org, Developer]:
    """Provision one org + one developer for the test. Clean up afterward."""
    org_id = uuid4()
    dev_id = uuid4()

    async with superuser_session() as db:
        org = Org(
            id=org_id,
            domain=f"e2e-{uuid4().hex[:8]}.test",
            name_ciphertext=b"\x00\x00\x00\x04fake",
            name_key_version=1,
            name_iv=b"\x00" * 12,
        )
        db.add(org)
        await db.flush()
        dev = Developer(
            id=dev_id,
            org_id=org_id,
            cognito_sub=f"cog-e2e-{uuid4()}",
            email_ciphertext=b"\x00\x00\x00\x04fake",
            email_key_version=1,
            email_iv=b"\x00" * 12,
            email_hash=uuid4().bytes,
        )
        db.add(dev)
        await db.flush()

    await reset_org_counters(org_id)

    yield (org, dev)

    # sessions.org_id is ON DELETE RESTRICT — delete sessions first, then org.
    async with superuser_session() as db:
        await db.execute(
            text("DELETE FROM sessions WHERE org_id = :id"), {"id": str(org_id)}
        )
        await db.execute(text("DELETE FROM orgs WHERE id = :id"), {"id": str(org_id)})
    await reset_org_counters(org_id)


async def test_pipeline_end_to_end(
    org_and_dev: tuple[Org, Developer],
) -> None:
    """Mimic the Ingest+Worker pipeline using only shared-lib helpers."""
    org, dev = org_and_dev
    session = _build_session(
        org_id=str(org.id),
        developer_id=str(dev.id),
        session_id=f"e2e-{uuid4()}",
        cost=1.23,
    )

    # ── Ingest leg ────────────────────────────────────────────────────────
    body = orjson.dumps(session.model_dump(mode="json"))
    gzipped = gzip.compress(body)
    s3_key = await put_raw_session(
        org_id=org.id,
        session_id=session.session_id,
        captured_at=session.meta.captured_at,
        body=gzipped,
    )
    assert s3_key.startswith(f"orgs/{org.id}/sessions/")

    # ── Worker leg ────────────────────────────────────────────────────────
    raw = await get_raw_session(s3_key)
    decompressed = gzip.decompress(raw)
    fetched = Session.model_validate(orjson.loads(decompressed))
    assert fetched.session_id == session.session_id

    async with org_scoped_session(org.id) as db:
        row_id = await upsert(
            db, fetched, developer_uuid=dev.id, org_uuid=org.id
        )
    assert row_id is not None

    await incr_session_count(org.id)
    await incr_cost_usd(org.id, fetched.tokens.total_cost_usd)

    # ── Verifications ─────────────────────────────────────────────────────
    async with org_scoped_session(org.id) as db:
        persisted = await get_by_external_id(
            db, org_uuid=org.id, external_session_id=session.session_id
        )
    assert persisted is not None
    assert persisted.tool_name == "claude-code"
    assert persisted.repo_branch == "feature/JIRA-142-test"
    assert float(persisted.total_cost_usd) == pytest.approx(1.23)

    summary = await get_today_summary(org.id)
    assert summary["sessions"] == 1
    assert summary["cost_usd"] == pytest.approx(1.23, abs=0.01)


async def test_pipeline_is_idempotent(
    org_and_dev: tuple[Org, Developer],
) -> None:
    """Submitting the same session twice = one DB row, but counters bump twice.

    (Idempotency on the DB is the hard guarantee. Counters intentionally
    over-count on retry and get reconciled hourly from Postgres truth —
    see Worker's processor.py docstring.)
    """
    org, dev = org_and_dev
    session = _build_session(
        org_id=str(org.id),
        developer_id=str(dev.id),
        session_id=f"idem-{uuid4()}",
        cost=0.50,
    )

    for _ in range(2):
        body = orjson.dumps(session.model_dump(mode="json"))
        gzipped = gzip.compress(body)
        await put_raw_session(
            org_id=org.id,
            session_id=session.session_id,
            captured_at=session.meta.captured_at,
            body=gzipped,
        )
        async with org_scoped_session(org.id) as db:
            await upsert(db, session, developer_uuid=dev.id, org_uuid=org.id)
        await incr_session_count(org.id)

    async with org_scoped_session(org.id) as db:
        result = await db.execute(
            text(
                "SELECT count(*) FROM sessions WHERE session_id = :sid"
            ),
            {"sid": session.session_id},
        )
        count = result.scalar_one()
    assert count == 1, "Idempotent upsert should produce exactly one row"

    summary = await get_today_summary(org.id)
    assert summary["sessions"] == 2  # counter does double on retry — accepted
