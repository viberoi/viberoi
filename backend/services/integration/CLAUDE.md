# CLAUDE.md — integration service

Owns ALL outbound HTTPS calls to GitHub / GitLab / Jira / Linear. OAuth flows, token lifecycle, webhook registration on the provider side, and the periodic + backfill sync that populates `tickets` and `sprints`.

No other service makes outbound calls to these providers. If you're tempted to write `httpx.get("https://api.github.com/...")` in `worker/` or `ingest/`, stop — wire a domain function here and call it from there via SQS/repository.

## Endpoint surface

| Method | Path | Caller | Auth |
|---|---|---|---|
| `GET` | `/integrations` | API service → frontend | Cognito JWT (any role) |
| `POST` | `/integrations/{provider}/connect` | frontend | Cognito JWT (OrgAdmin) |
| `GET` | `/integrations/{provider}/callback` | provider redirect | OAuth state token |
| `DELETE` | `/integrations/{provider}` | frontend | Cognito JWT (OrgAdmin) |
| `POST` | `/integrations/{provider}/sync` | manual + cron | Cognito JWT (OrgAdmin / TeamLead) |
| `GET` | `/healthz`, `/readyz` | LB | none |

Providers V1: `github` (App, not classic OAuth), `jira` (OAuth 2.0 3LO), `linear` (OAuth 2.0). Bitbucket / GitLab / Azure DevOps deferred to V2.

## OAuth state (CSRF)

- Generate via `viberoi_shared.integrations.oauth_state.generate_token()` (`secrets.token_urlsafe(32)`).
- Store in Redis (`STATE_TTL_SECONDS = 600`) via `oauth_state.store(...)`.
- Atomic single-use `GETDEL` on callback via `oauth_state.consume(...)`.
- The callback is **NOT** Cognito-authenticated — the state IS the auth. Verify it returns the right `provider` and rehydrate `(org_id, developer_id)` from the stored payload.

## Per-provider quirks

- **GitHub App** (not classic OAuth) — installation tokens (1h), re-mint from App JWT (RS256 signed with private key from Secrets Manager). No refresh token. Webhook is per-repo (POST `/repos/{owner}/{repo}/hooks`), one per repo the installation granted.
- **Jira** — OAuth 2.0 3LO. `offline_access` scope is mandatory for refresh tokens. Refresh tokens **rotate** — persist the new one. Discovery: `/oauth/token/accessible-resources` → `cloud_id`, plus `/rest/api/3/field` to find the Sprint custom field ID (varies per Jira instance).
- **Jira webhooks have NO HMAC scheme.** Authenticity rests on URL-secrecy + per-integration UUID. Document for security review.
- **Linear** — OAuth 2.0. Tokens valid ~10 years (no refresh in V1). `actor=application` recommended. Webhook via `webhookCreate` GraphQL mutation.

## Token refresh strategy

Lazy: when an outbound call is about to be made, check `expires_at <= now + 60s`. If so, refresh provider-specific (GitHub re-mints from App JWT; Jira POSTs `grant_type=refresh_token`; Linear never refreshes). Refresh failure → `revoke_token` + enqueue `notification_jobs` message → next `/sync` returns 410 Gone.

## Backfill sync

- Initial connect: synchronously enqueue `backfill_jobs` SQS message after token storage.
- Manual: `POST /sync` enqueues same.
- EventBridge cron: 5-min delta sync; a fan-out Lambda enumerates `integration_oauth_tokens` and publishes one message per (org, provider). (Lambda is its own batch.)
- Consumer runs in this service (`integration/app/consumer.py`) — the container launches `uvicorn` + the consumer side-by-side via `entrypoint.sh`.
- 90-day window for initial sync per spec § F3.
- Idempotent via `viberoi_shared.tickets.repository` upserts (keyed on `(org_id, system, external_id)`).

## Errors

- 429 (provider rate limited) → circuit breaker per (org, provider) in Redis. 3 failures in 5 min → open for 15 min → caller gets 429.
- 5xx (provider) → SQS NACK (no delete) → retry up to 3 times → DLQ.
- 401 (token expired and refresh failed) → revoke + notify + 410 Gone on next call.
- Bad OAuth state → 302 to `/settings/integrations?err=oauth_state`.

## Rules that apply

- Never write raw SQL — use `viberoi_shared.tickets`, `viberoi_shared.integrations`.
- Never `import httpx` directly except inside `integration/app/providers/` and `integration/app/http_client.py`.
- Never decrypt secrets outside `viberoi_shared.crypto.envelope` — the repository helpers do that for you.
- Per-service folder convention: `api/` (HTTP only) → `schema/` (Pydantic) → `app/` (orchestration + providers).
- Cognito JWT is **stubbed until Slice 5** — use FastAPI `dependency_overrides` in tests; production endpoints will raise `CognitoNotImplemented` until then.

## Slice 4 Batch C status

This service is being built incrementally in sub-batches. Current state:
- C1: skeleton + health + auth dependency + OAuth state shared module
- C2 (planned): full Cognito + HTTP client + circuit breaker + provider base
- C3: GitHub / Jira / Linear provider implementations
- C4: orchestrator + OAuth routes + list/disconnect + migration 0005
- C5: webhook registration + sync routines + consumer + commit
