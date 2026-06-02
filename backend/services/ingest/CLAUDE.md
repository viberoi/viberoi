# CLAUDE.md — ingest service

Receives session pushes from the Go agent, validates HMAC + `org_token`, writes raw payloads to S3 raw-landing, returns **202 immediately**. No processing. Processing happens in the Worker service, triggered by S3 events on the raw bucket.

## Endpoints

| Method | Path | Status |
|---|---|---|
| `POST` | `/ingest/session` | single session push |
| `POST` | `/ingest/sessions` | batch up to 100 |
| `POST` | `/ingest/register` | agent registration (Slice 5) |
| `GET` | `/agent/config` | org config for agent (Slice 5) |
| `GET` | `/agent/version` | agent update check (Slice 9) |
| `GET` | `/healthz` | liveness — fast, no deps |
| `GET` | `/readyz` | readiness — checks DB + S3 |

## Auth

HMAC-SHA256 with `org_token` (verified via `viberoi_shared.crypto.verify_secret`). Cognito JWT is **not** used on these endpoints — agents don't have JWTs.

## Slice 1 status (stub)

- Endpoints exist and validate Pydantic shape against `viberoi_shared.types.Session`
- `GET /healthz` + `/readyz` work
- **No HMAC verification yet** — lands when agent ships (Slice 9). Body is accepted as-is.
- **No S3 write yet** — lands in Slice 3 final implementation.
- **No developer profile creation yet** — `/ingest/register` is a placeholder; lands with Cognito (Slice 5).

## Rules that apply (from project-wide guides)

- Never raw SQL — use `viberoi_shared.sessions.upsert(...)`.
- Never raw S3 — use `viberoi_shared.s3` helpers (TBD).
- Always log via `viberoi_shared.logging.get_logger`.
- Errors raise typed exceptions; the registered FastAPI handler envelopes them.
- Per-service folder convention: `api/` (routes only) → `schema/` (Pydantic) → `app/` (orchestration).
