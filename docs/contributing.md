# Contributing to VibeROI

Solo-dev today, multi-dev tomorrow. These conventions exist so the codebase stays consistent across services and so future contributors don't have to ask the same questions twice.

## Read these first

- [`.claude/rules/structure.md`](../.claude/rules/structure.md) — folder layout, shared-library rule, file/function size, code reuse
- [`.claude/rules/security.md`](../.claude/rules/security.md) — auth, RLS, encryption, secrets, webhook HMAC
- [`docs/architecture.md`](architecture.md) — system overview and pointers into the sealed architecture docs

The `.claude/rules/` files are also loaded automatically by Claude Code and used to lint AI-generated code.

## Local setup

```powershell
# Prerequisites: Docker Desktop, Python 3.12, uv, git
# Optional: Go 1.22+ (only if working on agent/)

# Clone
git clone <repo-url> viberoi
cd viberoi

# Install Python workspace (run from repo root)
uv sync

# Bring up local infra (Postgres + Redis + LocalStack)
./scripts/dev-up.ps1        # or scripts/dev-up.sh on bash

# Apply migrations
uv run alembic upgrade head

# Run a service
uv run --package viberoi-ingest uvicorn ingest.main:app --reload
```

## The big rules in one page

1. **Shared lib owns infrastructure.** No service writes raw SQL, opens a DB/Redis connection, calls KMS, calls boto3 for SES/SNS/Slack, or instantiates a logger. Always `from viberoi_shared.<domain> import ...`.
2. **Per-service layout is `api/` + `schema/` + `app/`.** Routers (`api/`) never touch the DB; they call `app/` which calls `viberoi_shared/`.
3. **RLS is mandatory.** Every DB call goes through `viberoi_shared.db.org_scoped_session(org_id)`. Sets the GUC; Postgres enforces.
4. **Notification is queue-only.** No service ever calls Slack/Teams/SES synchronously. Use `viberoi_shared.notifications.enqueue(...)`.
5. **Privacy.** Never store prompts, code, diffs, PR descriptions, commit message bodies, or any content.
6. **Async everywhere.** `async def`, async SQLAlchemy, async Redis, async boto3 via `aioboto3`. All I/O has explicit timeouts.
7. **Type hints everywhere.** `mypy --strict` on shared; `mypy` on services.
8. **Pydantic at every boundary.** HTTP requests/responses, SQS messages, S3 envelopes, Cognito claims. No raw dicts cross service boundaries.
9. **File ≤ 400 lines, function ≤ 50 lines, ≤ 5 positional args, complexity ≤ 10.** Enforced by ruff.
10. **Three-strikes reuse rule.** Same logic in two services? Third write goes to shared.
11. **No cross-service imports.** Services import from `viberoi_shared` and stdlib only.
12. **One Alembic revision per schema change.** Migration includes matching RLS policy SQL.

## Workflow

- Branch naming: `feature/<area>-<short-desc>`, `fix/<area>-<short-desc>`, `chore/<...>`. Area examples: `ingest`, `worker`, `shared`, `infra`, `frontend`.
- Commit style: imperative subject ≤ 72 chars, body explains "why" not "what".
- One PR = one service or one shared module. Keep blast radius small.
- CI must be green before merge: lint, format, typecheck, tests.
- Migrations and RLS policies reviewed extra-carefully — bad RLS = data leak.

## What CI enforces

- **ruff check** — lint with the rules in `ruff.toml` (size, complexity, ANN, no-print, etc.)
- **ruff format --check** — formatting (Python black-compatible style)
- **mypy --strict** on `packages/shared/`
- **mypy** on `services/` and `lambdas/`
- **pytest** with Postgres + Redis service containers
- **No service imports another service** — a custom check on the import graph
- **No raw SQL strings** outside `viberoi_shared.db.*`
- **No `import boto3` in services** outside known wrappers (services use `viberoi_shared.*` boto helpers)

## Testing

- Unit tests live next to the code they cover (`tests/test_<module>.py`).
- Integration tests use real Postgres + Redis from docker-compose, not mocks (matches the user's stated preference for the project).
- LocalStack covers S3/SQS/KMS for tests that touch AWS APIs.
- One happy-path integration test per endpoint, minimum. Edge cases as you find them.
- `conftest.py` per service provides fixtures (test client, org, dev, JWT).

## Adding a new service

See [`docs/adding-a-service.md`](adding-a-service.md).

## Code review checklist

- [ ] Does this need a migration? Is RLS attached?
- [ ] Does this write to a new column? Is it PII (encrypt) or plaintext-safe?
- [ ] Does this call an external API? Through `viberoi_shared.<integration>` or directly? (Must be through shared.)
- [ ] Does this log user content by accident? (Especially error paths.)
- [ ] Does this add a new env var? Is it in `.env.example`? Is the prod value in Secrets Manager?
- [ ] Did file or function size limits get crossed? Justification in the PR?
- [ ] Are types complete? `mypy --strict` clean on the changed modules?
- [ ] Tests added or updated?
