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
