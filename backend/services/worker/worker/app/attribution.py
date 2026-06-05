"""Attribution signals.

Locked spec: `frontend/VibeROI-DataSource-Master-final.md` § Q5.

Signals 1, 2, and 5 are live. Signals 3 + 4 still need data sources we
haven't ingested yet:

  - Signal 1 (branch parse)         BUILT  0.35
  - Signal 2 (file overlap)         BUILT  0.25  needs ticket.pr_file_paths
  - Signal 3 (temporal proximity)   stub   0.20  needs ticket "In Progress" ts
  - Signal 4 (developer match)      stub   0.15  needs ticket.assignee
  - Signal 5 (explicit mention)     BUILT  0.05  ticket.title contains ticket_id

`attribute(session)` runs Signal 1 with the session alone — that's the
sync path the agent ingest uses. `enrich_with_db_signals(attr,
session, db)` runs Signals 2 + 5 if the ticket already exists in DB
(populated by the webhook handler).

Privacy: Signal 5 reads `ticket.title` only. Bodies/descriptions never
land in our DB so they can't be considered.
"""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from viberoi_shared.types import Attribution
from viberoi_shared.types.enums import AttributionMethod
from viberoi_shared.types.session import Session

# Matches:
#   JIRA-142, ENG-89, ABC-123  (uppercase prefix + digits)
#   #142                       (GitHub issue style)
# No word boundaries — `\b` doesn't work for `#` since it isn't a word
# character. Uppercase-required start keeps false positives away from
# lowercase branch identifiers like "claude/xenodochial-..." or "wip-auth".
_BRANCH_TICKET_RE = re.compile(r"([A-Z][A-Z0-9]+-\d+|#\d+)")

# Signal weights from spec § Q5.
SIGNAL_BRANCH_WEIGHT = 0.35
SIGNAL_FILE_OVERLAP_WEIGHT = 0.25
SIGNAL_EXPLICIT_MENTION_WEIGHT = 0.05


def parse_branch_for_ticket(branch: str) -> str | None:
    """Extract a ticket ID from a branch name. Returns None if no match."""
    if not branch:
        return None
    match = _BRANCH_TICKET_RE.search(branch)
    return match.group(1) if match else None


def attribute(session: Session) -> Attribution:
    """Compute attribution from session-only data (Signal 1 alone).

    Returns a new `Attribution` (the input is treated as advisory).
    The caller may follow up with `enrich_with_db_signals` once a DB
    session is open.
    """
    ticket_id = parse_branch_for_ticket(session.repository.branch)
    signals: list[str] = []
    confidence = 0.0

    if ticket_id:
        signals.append("branch_match")
        confidence = SIGNAL_BRANCH_WEIGHT

    return Attribution(
        ticket_id=ticket_id,
        epic_id=None,  # backfilled from Jira/Linear in Phase F
        sprint_id=None,
        confidence=confidence,
        signals=signals,
        method=AttributionMethod.BRANCH_PARSE,
    )


async def enrich_with_db_signals(
    attr: Attribution, session: Session, db: AsyncSession
) -> Attribution:
    """Add Signals 2 + 5 to an existing Attribution when ticket data
    already exists in DB.

    No-op when:
      - `attr.ticket_id` is None (nothing to look up)
      - No matching ticket row exists yet (webhook hasn't arrived)

    Both signals only ADD confidence — they never demote a Signal-1
    branch match. Worker re-runs attribution on the every-5-min
    backfill cron when more data arrives.
    """
    if not attr.ticket_id:
        return attr

    rows = await db.execute(
        text(
            """
            SELECT title, pr_file_paths
            FROM tickets
            WHERE external_id = :ext
              AND org_id = :org
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ),
        {"ext": attr.ticket_id, "org": session.org_id},
    )
    row = rows.first()
    if row is None:
        return attr

    title, pr_file_paths = row
    new_signals = list(attr.signals)
    new_confidence = float(attr.confidence)

    # Signal 2: file overlap. Any of the session's touched paths show
    # up in the ticket's known PR file list -> fires (binary signal;
    # depth of overlap doesn't increase weight here, spec doesn't
    # mandate it).
    session_files = set(session.activity.files_touched or [])
    ticket_files = set(pr_file_paths or [])
    if session_files and ticket_files and session_files & ticket_files:
        new_signals.append("file_overlap")
        new_confidence += SIGNAL_FILE_OVERLAP_WEIGHT

    # Signal 5: explicit mention. Ticket's TITLE references the ticket
    # id (e.g. PR title "JIRA-142: payment fix"). Bodies are never
    # considered (privacy rule).
    if title and attr.ticket_id in title:
        new_signals.append("explicit_mention")
        new_confidence += SIGNAL_EXPLICIT_MENTION_WEIGHT

    # Floor at the pre-enrichment value (defense — never demote).
    new_confidence = max(new_confidence, float(attr.confidence))

    return attr.model_copy(
        update={
            "signals": new_signals,
            "confidence": new_confidence,
        }
    )
