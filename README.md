# VibeROI

Privacy-first AI engineering ROI / observability platform.

Captures AI coding-tool usage from developer machines (Claude Code, Cursor, Kiro, Copilot), attributes sessions to tickets and sprints, and gives engineering leaders the metrics needed to justify, optimise, and govern AI spend — **without reading prompts or code**.

## Documentation

- **Business requirements:** [`BRD-v1.0.md`](BRD-v1.0.md)
- **Functional spec:** [`FSD-v1.0-final.md`](FSD-v1.0-final.md)
- **System architecture & data sources:** [`frontend/VibeROI-DataSource-Master-final.md`](frontend/VibeROI-DataSource-Master-final.md)
- **Contributing & coding standards:** [`docs/contributing.md`](docs/contributing.md)
- **System overview & service map:** [`docs/architecture.md`](docs/architecture.md)

## Repo layout

```
backend/            All Python — services, lambdas, shared library, migrations
  packages/shared/  Shared library: DB, Redis, crypto, logging, errors, domain types
  services/         6 ECS Fargate services: ingest, api, auth, worker, integration, notification
  lambdas/          Webhook receiver + Cognito triggers + EventBridge crons
  migrations/       Alembic — single source of truth for schema + RLS
frontend/           React SPA (Vite + Tremor + TanStack Query)
agent/              Go daemon (cross-platform local IDE-data collector)
infra/              Terraform + Dockerfiles (deploys all of the above)
scripts/            docker-compose helpers, dev workflow
docs/               Human-readable architecture, contributing, runbooks
```

Python tooling (`uv`, `ruff`, `mypy`, `pytest`) runs from the repo root — the root `pyproject.toml` is the uv workspace owner.

## Quickstart (local dev)

```powershell
# 1. Bring up Postgres + Redis + LocalStack (S3 + SQS + KMS)
./scripts/dev-up.ps1

# 2. Install workspace deps
uv sync

# 3. Apply DB migrations
uv run alembic upgrade head

# 4. Run a service locally (example: ingest, once Slice 3 lands)
uv run --package viberoi-ingest uvicorn ingest.main:app --reload
```

Bash equivalents in `scripts/dev-up.sh`.

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2 (async) + asyncpg · Alembic · Pydantic 2 · structlog · uv workspaces · AWS Cognito · RDS Postgres + RLS · ElastiCache Redis · SQS · S3 · ECS Fargate · Terraform · GitHub Actions

Agent: Go 1.22+ (single binary, cross-platform).

## Privacy principle

Hard rule: never store prompts, code, diffs, PR descriptions, commit messages, or any user-generated content. Only metadata — token counts, timestamps, file paths, branch names, commit hashes.
