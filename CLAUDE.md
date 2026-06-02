# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What VibeROI is

Privacy-first AI engineering ROI/observability platform. Captures AI coding-tool metadata (tokens, file paths, timestamps — **never prompts or code**), attributes sessions to tickets/sprints, surfaces ROI/quality KPIs.

**Authoritative architecture:** `frontend/VibeROI-DataSource-Master-final.md` (locked: session schema v1.0, attribution engine, cloud deploy, agent design, API surface). Read this before changing anything load-bearing. Business & functional specs in `BRD-v1.0.md` and `FSD-v1.0-final.md`.

## Stack (locked)

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 async + asyncpg, Pydantic 2, Alembic
- **Auth:** AWS Cognito (PreSignUp + PostConfirmation Lambdas in `backend/lambdas/`)
- **Data:** RDS Postgres + Row-Level Security, ElastiCache Redis, SQS, S3
- **Agent:** Go (separate binary in `agent/`, outside `backend/`)
- **Frontend:** Vite + React + TS + Tremor + TanStack Query
- **Infra:** Terraform; ECS Fargate; Lambdas as container images (same base as services)
- **Local dev:** docker-compose (Postgres + Redis + LocalStack for S3/SQS/KMS)
- **Package manager:** uv (workspace mode)
- **CI:** GitHub Actions

## Non-negotiable rules

These are enforced by ruff, mypy, and review. Read before generating code:

- [`.claude/rules/structure.md`](.claude/rules/structure.md) — folder layout, shared-library rule, file/function size limits, code-reuse policy
- [`.claude/rules/security.md`](.claude/rules/security.md) — RLS enforcement, Cognito JWT, KMS+Argon2 crypto, webhook HMAC, no-content-stored

## Quick reminders

- **Never** write raw SQL or open a DB connection in a service. Use `viberoi_shared.<domain>.<func>`.
- **Never** call Slack/Teams/Email/SES directly. Enqueue via `viberoi_shared.notifications.enqueue(...)`.
- **Never** store prompts, code, diffs, PR descriptions, or commit-message bodies. Metadata only.
- **Always** set `app.current_org_id` via the shared session helper before any DB call. RLS depends on it.
- **Argon2id** for hashing secrets (org_token, webhook signing keys). **KMS + AES-256-GCM** for PII at rest. Both via `viberoi_shared.crypto`.
- Session-object schema is locked at v1.0 (`viberoi_shared.types.session.Session`). Bump `schema_version` for any change.
- Lambdas are container images sharing the same Dockerfile base as services — `viberoi_shared` is consumed identically.

## Common commands

All commands run from the repo root (root `pyproject.toml` is the uv workspace owner):

```powershell
./scripts/dev-up.ps1              # local infra: Postgres + Redis + LocalStack
./scripts/dev-down.ps1            # tear down
uv sync                           # install all workspace deps
uv run alembic upgrade head       # apply migrations
uv run pytest                     # run all tests
uv run ruff check .               # lint
uv run ruff format .              # format
uv run mypy backend/packages/shared    # strict typecheck on shared
```

## Service-specific guidance

Each `backend/services/<name>/` and `backend/lambdas/<name>/` may have its own `CLAUDE.md` for module-specific quirks. Add one when a service has non-obvious behavior the rules above don't cover.
