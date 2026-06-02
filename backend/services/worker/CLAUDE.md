# CLAUDE.md — worker service

Consumes S3 events from SQS `session_ingest`, GETs the raw session from S3, validates the locked v1.0 schema, runs attribution, upserts into Postgres, and (Slice 3 follow-up) increments Redis counters for live KPIs.

## Loop

Long-polls SQS (`wait_seconds=20`, batch up to 10). Per message:

1. Parse S3 event envelope (Pydantic — `worker.schema.events.S3EventEnvelope`)
2. For each S3 record in the envelope:
   - `viberoi_shared.s3.get_raw_session(key)` → gunzip
   - Validate against `viberoi_shared.types.Session`
   - Recompute attribution (the Worker is the source of truth, not the agent)
   - `viberoi_shared.sessions.upsert(...)` inside `org_scoped_session(session.org_id)` (RLS-enforced)
3. Ack the SQS message via `viberoi_shared.sqs.delete(...)`

On any processing error: **do NOT ack** → SQS makes the message visible again after the queue's VisibilityTimeout (30s) → DLQ after `maxReceiveCount=3` attempts. The DLQ has a CloudWatch alarm in prod (Terraform module, Slice 8).

## Slice 3 status

- **Implemented:** Signal 1 (branch parse) in `app/attribution.py`. Pipeline end-to-end.
- **Stubbed:** Signals 2/3/4 — require ticket/PR data from Jira/Linear/GitHub. Lands with Integration service (Slice 4).
- **Stubbed:** Signal 5 (explicit mention) — requires commit-message body + PR title from webhooks. Lands with webhook Lambda (Slice 4).
- **Stubbed:** Redis counter increments — Task 18 of this slice (separate file).
- **Stubbed:** Hallucination loop detection (`quality.*` recomputation). Lands when we have the per-turn token series.

## Rules that apply

- Never raw SQL — use `viberoi_shared.sessions.upsert` and `viberoi_shared.sessions.get_by_external_id`.
- Always set RLS context via `org_scoped_session(org_id)` before any DB call.
- All AWS access via `viberoi_shared.aws` helpers.
- Errors raise typed exceptions; the consumer catches them and intentionally does NOT ack the message so SQS retries.

## Not in this service

- No HTTP endpoints — Worker is a pure consumer. ECS detects dead containers via process exit; production observability is via CloudWatch metrics on SQS depth + DLQ.
- No notification delivery — Worker enqueues to `notification_jobs` via `viberoi_shared.notifications.enqueue(...)` (Slice 5); the Notification service delivers.
