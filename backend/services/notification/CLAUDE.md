# CLAUDE.md — notification service

Drains SQS `notification_jobs`, looks up the org's channel config,
renders a template, delivers. Pure consumer (no HTTP). Only this
service makes outbound HTTPS to Slack/Teams; only this service calls
SES. Other services enqueue via `viberoi_shared.notifications.enqueue`.

## Loop

Long-poll SQS (`wait_seconds=20`, batch up to 5). Per message:

1. Parse `NotificationEnvelope` (Pydantic; bad envelope → ack so it
   doesn't loop forever).
2. Check the per-(org, channel) circuit breaker. Open → ack (don't
   retry) + log + return.
3. `superuser_session()` → `get_channel_for_org(...)` to load decrypted
   webhook URL (Slack) or recipient config (email). Missing or
   disabled → ack + log; nothing to deliver.
4. Look up the template renderer; renderer turns the envelope's
   `payload` into a channel-specific payload (Slack `blocks` array,
   email subject/body).
5. Hand off to the channel handler:
   - Slack → `httpx.post(webhook_url, json=...)` with 5s timeout.
   - Teams → V2.
   - Email → SES `SendEmail` (V2; V1 logs + acks).
6. On success: `circuit_breaker.record_success`, ack.
7. On HTTP failure: `circuit_breaker.record_failure`. Do NOT ack —
   SQS will redeliver. After 3 failures in 5 min the breaker opens
   and downstream calls short-circuit; eventually the SQS DLQ kicks
   in (`maxReceiveCount=3`).

## Templates

Registered in `app/templates.py` as `{name: callable(payload) ->
ChannelPayload}`. V1 templates (start with what we actually emit):

- `integration_revoked` — "Your <provider> integration was revoked
  because the token refresh failed. Re-connect at <url>."
- `hallucination_loop_detected` — "Session <id> triggered the
  hallucination-loop signal; reviewed cost: $X."

Adding a template: append to the registry, write a test, done. No
Jinja, no fetch from S3, no string formatting outside the template
function (which is the only place where allowed substitutions live).

Templates NEVER reference user content beyond what's already in the
envelope payload — they don't fetch sessions, decode PII, or look up
emails. The caller of `enqueue` puts everything the template needs
into `payload`.

## Channel handlers

- `app/handlers/slack.py` — Slack incoming-webhook POST. Returns
  `ok` on 200, `transient` on 5xx, `permanent` on 4xx (other than
  429). Permanent failures disable the channel via
  `disable_channel(...)`.
- `app/handlers/noop.py` — used by tests + the (unused-in-prod)
  `"noop"` channel value. Always succeeds.

## Circuit breaker

Per-(org, channel) Redis key:
`notif:cb:{org}:{channel}` → JSON `{failures, opened_at}`.

- `record_failure` → increment failures, set `opened_at` once
  failures crosses the threshold (default 3 within 5 min window).
- `is_open` → check `opened_at` is within 15 min of now.
- `record_success` → delete the key.

## Rules that apply

- Never write raw SQL — use `viberoi_shared.notifications` repository.
- Never decrypt webhook URLs outside `get_channel_for_org`.
- Never log the webhook URL, message body, or recipient email.
  Log `org_id`, `channel`, `template`, `trace_id`, outcome only.
- Never import boto3 directly (use `viberoi_shared.aws`).
- Never call Slack/Teams/SES from any other service.
