"""Webhook event router.

Receives a verified webhook envelope from SQS `webhook_events` (pushed
by the Lambda receiver) and dispatches to the provider-specific event
handler. Each handler updates `tickets` (pr_file_paths, titles, etc.)
so the next attribution pass can fire Signals 2 + 5.

Privacy hard line: we MAY persist commit/PR titles for Signal 5; we
MUST NOT persist commit-message bodies, PR descriptions, or any other
free-form text (security.md). The handlers below extract only titles
+ file paths.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from viberoi_shared.db import org_scoped_session
from viberoi_shared.logging import bind_request_context, get_logger
from viberoi_shared.tickets import upsert_ticket

from worker.schema.webhook_events import WebhookEnvelope

logger = get_logger(__name__)


# ── Top-level dispatch ─────────────────────────────────────────────────────


async def process_webhook(envelope: WebhookEnvelope) -> None:
    """Route a verified webhook envelope to the right provider handler."""
    bind_request_context(
        request_id=f"webhook:{envelope.provider}:{envelope.delivery_id}"
    )
    event_type = envelope.event_type()
    if event_type is None:
        logger.warning("webhook_event_type_missing", provider=envelope.provider)
        return

    org_uuid = UUID(envelope.org_id)
    try:
        body = envelope.parsed_body()
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "webhook_body_unparseable",
            provider=envelope.provider,
            event=event_type,
            error=str(e),
        )
        return

    if envelope.provider == "github":
        await _process_github(org_uuid, event_type, body)
    elif envelope.provider == "gitlab":
        # V2 — pattern is the same; we just don't have the parsers yet.
        logger.info("webhook_gitlab_unhandled", event=event_type)
    elif envelope.provider == "linear":
        # V2.
        logger.info("webhook_linear_unhandled", event=event_type)
    else:
        logger.warning("webhook_provider_unknown", provider=envelope.provider)


# ── GitHub event handlers ──────────────────────────────────────────────────


async def _process_github(
    org_id: UUID, event_type: str, body: dict[str, Any]
) -> None:
    if event_type == "pull_request":
        await _handle_github_pull_request(org_id, body)
    elif event_type == "push":
        await _handle_github_push(org_id, body)
    elif event_type == "ping":
        # GitHub sends ping on webhook creation. Acknowledge silently.
        return
    else:
        logger.info("github_event_unhandled", event=event_type)


async def _handle_github_pull_request(org_id: UUID, body: dict[str, Any]) -> None:
    """Extract PR title + changed file paths from a pull_request event.

    Persisted to tickets.{title, pr_file_paths} keyed on
    (system='github_pr', external_id='owner/repo#number'). Body
    ignored per privacy rule — only title is OK for attribution.
    """
    action = body.get("action")
    if action not in {"opened", "edited", "synchronize", "reopened", "closed"}:
        logger.info("github_pr_action_skipped", action=action)
        return

    pr = body.get("pull_request") or {}
    repo = body.get("repository") or {}
    repo_full_name = repo.get("full_name")
    number = pr.get("number")
    title = pr.get("title")
    if not (repo_full_name and number and title):
        logger.warning(
            "github_pr_missing_fields",
            has_repo=bool(repo_full_name),
            has_number=bool(number),
            has_title=bool(title),
        )
        return

    external_id = f"{repo_full_name}#{number}"

    # PR file paths — included on payload for small PRs; for large ones
    # GitHub requires a follow-up GET /pulls/{n}/files call (paginated,
    # up to 30 files per page, 3000 max). For V1, take what's on the
    # payload; the integration service's sync() will fill the rest on
    # the next scheduled run.
    file_paths: list[str] = []
    for f in body.get("files") or []:
        path = f.get("filename")
        if path:
            file_paths.append(path)

    closed_at: datetime | None = None
    if action == "closed" and pr.get("merged_at"):
        # We treat merged-PR closing as the canonical "done" timestamp;
        # closed-without-merge is also closed but distinguishable via
        # status (we don't track that yet — store both as 'closed').
        try:
            closed_at = datetime.fromisoformat(
                pr["merged_at"].replace("Z", "+00:00")
            )
        except Exception:  # noqa: BLE001
            closed_at = datetime.now(tz=UTC)

    created_at_external: datetime | None = None
    if pr.get("created_at"):
        try:
            created_at_external = datetime.fromisoformat(
                pr["created_at"].replace("Z", "+00:00")
            )
        except Exception:  # noqa: BLE001
            pass

    async with org_scoped_session(org_id) as db:
        await upsert_ticket(
            db,
            org_id=org_id,
            system="github_pr",
            external_id=external_id,
            title=title,
            status="closed" if closed_at else "open",
            created_at_external=created_at_external,
            closed_at_external=closed_at,
            pr_file_paths=file_paths or None,
        )

    logger.info(
        "github_pr_ingested",
        action=action,
        external_id=external_id,
        files=len(file_paths),
    )


async def _handle_github_push(org_id: UUID, body: dict[str, Any]) -> None:
    """Push events tell us commit titles + the branch. We record commit
    titles on the ticket the branch references (e.g. branch
    'feature/ABC-123' → ticket external_id 'ABC-123' on whichever
    ticket system matches).

    Branch parsing happens already at session ingestion (Signal 1); the
    purpose here is to keep ticket metadata fresh as work progresses
    + provide commit titles for Signal 5.
    """
    ref = body.get("ref") or ""
    if not ref.startswith("refs/heads/"):
        # Tag pushes, deletes, etc.
        return
    branch = ref[len("refs/heads/") :]

    commits = body.get("commits") or []
    # Privacy: only the message *title* (first line). Body forbidden.
    titles: list[str] = []
    for c in commits:
        msg = c.get("message") or ""
        title = msg.splitlines()[0] if msg else ""
        if title:
            titles.append(title)

    logger.info(
        "github_push_received",
        branch=branch,
        commits=len(commits),
        title_count=len(titles),
    )
    # NOTE: we don't write commit titles to the DB yet — the schema has
    # no `commit_titles` column on tickets. Signal 5 in attribution.py
    # will need it; the column lands in a follow-up migration when
    # we wire E-3.
