"""Attribution signals.

Locked spec: `frontend/VibeROI-DataSource-Master-final.md` § Q5.

Slice 3 implements Signal 1 (branch parse) only. The other signals
depend on data sources that arrive in later slices:

  - Signal 2 (file overlap) — needs PR file list from GitHub (Slice 4)
  - Signal 3 (temporal proximity) — needs ticket "In Progress" timestamps from Jira/Linear (Slice 4)
  - Signal 4 (developer match) — needs ticket.assignee from Jira/Linear (Slice 4)
  - Signal 5 (explicit mention) — needs commit message bodies + PR title from webhooks (Slice 4)

When those land, Worker re-attributes via backfill (every 5 min cron)
and pulls confidence from <0.50 (unknown queue) up toward 1.0.
"""

import re

from viberoi_shared.types import Attribution
from viberoi_shared.types.enums import AttributionMethod
from viberoi_shared.types.session import Session

# Matches:
#   JIRA-142, ENG-89, ABC-123  (uppercase prefix + digits)
#   #142                       (GitHub issue style)
# Word boundaries prevent partial matches inside other identifiers.
_BRANCH_TICKET_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+|#\d+)\b")

# Signal weights from spec § Q5.
SIGNAL_BRANCH_WEIGHT = 0.35


def parse_branch_for_ticket(branch: str) -> str | None:
    """Extract a ticket ID from a branch name. Returns None if no match."""
    if not branch:
        return None
    match = _BRANCH_TICKET_RE.search(branch)
    return match.group(1) if match else None


def attribute(session: Session) -> Attribution:
    """Compute attribution for a session given the data available right now.

    Returns a new `Attribution` (the input is treated as advisory).
    """
    ticket_id = parse_branch_for_ticket(session.repository.branch)
    signals: list[str] = []
    confidence = 0.0

    if ticket_id:
        signals.append("branch_match")
        confidence = SIGNAL_BRANCH_WEIGHT

    return Attribution(
        ticket_id=ticket_id,
        epic_id=None,  # backfilled from Jira/Linear in Slice 4
        sprint_id=None,  # backfilled from Jira/Linear in Slice 4
        confidence=confidence,
        signals=signals,
        method=AttributionMethod.BRANCH_PARSE,
    )
