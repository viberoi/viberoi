"""Unit tests for attribution Signal 1 (branch parse)."""

from datetime import UTC, datetime

import pytest

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
    AttributionMethod,
    CaptureMode,
    HallucinationRisk,
    PricingType,
    PricingUnit,
    SessionMode,
    Surface,
    Tool,
)
from worker.app.attribution import (
    SIGNAL_BRANCH_WEIGHT,
    attribute,
    parse_branch_for_ticket,
)


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("feature/JIRA-142-payment-gateway", "JIRA-142"),
        ("feature/ENG-89-auth-refactor", "ENG-89"),
        ("bugfix/ABC-1-fix-typo", "ABC-1"),
        ("hotfix/PROJ-9999", "PROJ-9999"),
        ("feature/JIRA-142-and-JIRA-200", "JIRA-142"),  # first match wins
        ("feat/#42-something", "#42"),  # GitHub issue style
    ],
)
def test_parse_branch_extracts_ticket(branch: str, expected: str) -> None:
    assert parse_branch_for_ticket(branch) == expected


@pytest.mark.parametrize(
    "branch",
    [
        "main",
        "feature/no-ticket-here",
        "patch-2",
        "wip-auth",
        "claude/xenodochial-joliot-361764",
        "jira-142-lowercase-no-match",  # uppercase prefix required
        "",
    ],
)
def test_parse_branch_returns_none(branch: str) -> None:
    assert parse_branch_for_ticket(branch) is None


def _session_with_branch(branch: str) -> Session:
    """Build a minimal valid Session with the given branch."""
    now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=UTC)
    return Session(
        session_id="s1",
        developer_id="00000000-0000-0000-0000-000000000001",
        org_id="00000000-0000-0000-0000-000000000002",
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
        repository=Repository(name="r", origin_cwd="/r", branch=branch),
        attribution=Attribution(),  # advisory; attribute() recomputes
        quality=Quality(hallucination_risk=HallucinationRisk.NONE),
        meta=Meta(captured_at=now, agent_version="0.1.0"),
    )


def test_attribute_with_matching_branch() -> None:
    session = _session_with_branch("feature/JIRA-142-payment")
    result = attribute(session)
    assert result.ticket_id == "JIRA-142"
    assert result.confidence == pytest.approx(SIGNAL_BRANCH_WEIGHT)
    assert "branch_match" in result.signals
    assert result.method is AttributionMethod.BRANCH_PARSE


def test_attribute_with_no_match() -> None:
    session = _session_with_branch("main")
    result = attribute(session)
    assert result.ticket_id is None
    assert result.confidence == 0.0
    assert result.signals == []
    assert result.method is AttributionMethod.BRANCH_PARSE


def test_attribute_ignores_agent_supplied_attribution() -> None:
    """The agent's attribution is advisory; Worker recomputes."""
    session = _session_with_branch("main")
    # Even if the agent claims a ticket, Worker's output should reflect
    # only what the signals say.
    session = session.model_copy(
        update={
            "attribution": Attribution(
                ticket_id="JIRA-999",
                confidence=0.95,
                signals=["agent_claim"],
                method=AttributionMethod.MANUAL,
            )
        }
    )
    result = attribute(session)
    assert result.ticket_id is None
    assert result.confidence == 0.0


def test_attribute_epic_and_sprint_stubbed_for_now() -> None:
    """Backfill from Jira/Linear populates these in Slice 4."""
    session = _session_with_branch("feature/JIRA-142")
    result = attribute(session)
    assert result.epic_id is None
    assert result.sprint_id is None


# ── Signals 2 + 5 (DB enrichment) ─────────────────────────────────────────


from unittest.mock import AsyncMock, MagicMock

from worker.app.attribution import (
    SIGNAL_FILE_OVERLAP_WEIGHT,
    SIGNAL_EXPLICIT_MENTION_WEIGHT,
    enrich_with_db_signals,
)


def _session_with(branch: str, files_touched: list[str]) -> Session:
    s = _session_with_branch(branch)
    return s.model_copy(
        update={
            "activity": s.activity.model_copy(
                update={
                    "files_touched": files_touched,
                    "files_touched_count": len(files_touched),
                }
            )
        }
    )


def _mock_db_returning(row: tuple | None) -> AsyncMock:
    """Returns a stub AsyncSession whose `execute().first()` yields `row`."""
    db = MagicMock()
    result = MagicMock()
    result.first.return_value = row
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_enrich_no_op_when_no_ticket_id() -> None:
    s = _session_with_branch("main")
    attr = attribute(s)
    db = _mock_db_returning(None)
    result = await enrich_with_db_signals(attr, s, db)
    assert result.confidence == 0.0
    assert result.signals == []
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_enrich_no_op_when_ticket_not_in_db() -> None:
    s = _session_with("feature/JIRA-142", ["src/a.py"])
    attr = attribute(s)
    db = _mock_db_returning(None)
    result = await enrich_with_db_signals(attr, s, db)
    # Only Signal 1 weight remains.
    assert result.confidence == pytest.approx(SIGNAL_BRANCH_WEIGHT)
    assert result.signals == ["branch_match"]


@pytest.mark.asyncio
async def test_enrich_signal_2_file_overlap_fires() -> None:
    s = _session_with("feature/JIRA-142", ["src/auth.py", "tests/test_x.py"])
    attr = attribute(s)
    db = _mock_db_returning(("[no mention]", ["src/auth.py", "src/other.py"]))
    result = await enrich_with_db_signals(attr, s, db)
    assert "file_overlap" in result.signals
    assert "explicit_mention" not in result.signals
    assert result.confidence == pytest.approx(
        SIGNAL_BRANCH_WEIGHT + SIGNAL_FILE_OVERLAP_WEIGHT
    )


@pytest.mark.asyncio
async def test_enrich_signal_5_explicit_mention_fires() -> None:
    s = _session_with("feature/JIRA-142", ["src/foo.py"])
    attr = attribute(s)
    db = _mock_db_returning(("JIRA-142: implement payment", []))
    result = await enrich_with_db_signals(attr, s, db)
    assert "explicit_mention" in result.signals
    assert "file_overlap" not in result.signals
    assert result.confidence == pytest.approx(
        SIGNAL_BRANCH_WEIGHT + SIGNAL_EXPLICIT_MENTION_WEIGHT
    )


@pytest.mark.asyncio
async def test_enrich_both_signals_stack() -> None:
    s = _session_with("feature/JIRA-142", ["src/auth.py"])
    attr = attribute(s)
    db = _mock_db_returning(("JIRA-142: auth refactor", ["src/auth.py"]))
    result = await enrich_with_db_signals(attr, s, db)
    assert "file_overlap" in result.signals
    assert "explicit_mention" in result.signals
    expected = (
        SIGNAL_BRANCH_WEIGHT
        + SIGNAL_FILE_OVERLAP_WEIGHT
        + SIGNAL_EXPLICIT_MENTION_WEIGHT
    )
    assert result.confidence == pytest.approx(expected)


@pytest.mark.asyncio
async def test_enrich_does_not_demote_confidence() -> None:
    """Hand-craft a synthetic high-confidence Attribution and ensure
    enrichment never lowers it (defense against future weight changes)."""
    s = _session_with("feature/JIRA-142", ["src/foo.py"])
    attr = Attribution(
        ticket_id="JIRA-142",
        confidence=0.9,
        signals=["branch_match"],
        method=AttributionMethod.BRANCH_PARSE,
    )
    db = _mock_db_returning(("[no mention]", []))  # no signals fire
    result = await enrich_with_db_signals(attr, s, db)
    assert result.confidence == pytest.approx(0.9)
