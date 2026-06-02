---
description: Repo layout, shared-library rule, per-service folder convention, file/function size limits, code-reuse policy. Enforced via ruff, mypy, and review.
---

# Structure Rules

Enforced via ruff, mypy, and code review. Breaking them is rare and must be justified in the PR.

## Repo layout

```
backend/                          All Python lives here
  packages/shared/                The ONLY place DB/Redis/crypto/log/error code lives
    viberoi_shared/
      db/                         async engine, RLS context, session factory
      sessions/                   CRUD + ORM for sessions table
      tickets/                    CRUD + ORM for tickets, sprints
      orgs/                       CRUD + ORM for orgs, developers, RBAC
      kpis/                       snapshot read/write
      redis/                      adapter, pub/sub helpers, namespacing
      sqs/                        publish/consume helpers
      s3/                         raw-landing read/write
      cognito/                    JWT validation, JWKS cache
      crypto/                     Argon2id hashing + KMS envelope encryption
      notifications/              enqueue helper (services NEVER deliver directly)
      webhooks/                   HMAC verification per provider
      lambda_auth/                per-trigger Lambda authentication
      aws/                        boto3 / aioboto3 client factories
      secrets/                    Secrets Manager wrapper, local-dev override
      logging/                    structlog config, request_id middleware, PII scrubbing
      errors/                     typed exceptions + FastAPI handlers
      types/                      Pydantic models shared across services
      config/                     settings loader (pydantic-settings)
  services/                       ECS Fargate services
    <service>/
      <service>/
        api/                      FastAPI routers — HTTP shape ONLY, no business logic
        schema/                   Pydantic request/response models
        app/                      orchestration + service-specific logic
        main.py                   FastAPI app entry; wires routers + middleware
      tests/
      pyproject.toml              independent deps; depends on viberoi-shared
      Dockerfile
  lambdas/                        Same Dockerfile base as services
    <lambda>/
      handler.py
      tests/
      pyproject.toml
      Dockerfile
  migrations/                     Alembic — single source of truth for schema
    versions/
    rls_policies/                 RLS SQL versioned alongside DDL

frontend/                         Vite + React + TS + Tremor (scaffolded in Slice 5/6)

agent/                            Go daemon — see agent/CLAUDE.md (separate language, separate rules)

infra/
  docker/                         base.Dockerfile, service.Dockerfile, lambda.Dockerfile
  terraform/
    modules/                      vpc, rds, redis, ecs-service, lambda, cognito, etc.
    envs/{dev,staging,prod}/
    bootstrap/                    state bucket + lock table (one-time apply)

scripts/                          docker-compose helpers, seed data, dev workflow
docs/                             architecture, contributing, runbooks, ADRs
.github/workflows/                CI: lint, typecheck, test on PR; deploy on tag

pyproject.toml                    uv workspace root (members → backend/*)
ruff.toml                         lint rules
CLAUDE.md                         Claude Code session anchor
```

The root `pyproject.toml` owns the uv workspace; run `uv sync`, `uv run`, `ruff`, `mypy`, `pytest` from the repo root.

## The shared-library rule

**Every cross-cutting concern lives in `packages/shared/`. Services consume it; they never reimplement it.**

What belongs in shared:
- DB adapters (every CRUD function — services pass params, never write SQL inline)
- Redis adapter
- Structured logging (request_id, org_id, service, event)
- Error types + handlers
- Cognito JWT validation
- SQS publish/consume
- S3 read/write
- KMS encryption + Argon2 hashing
- Notification enqueue
- Shared domain types

What belongs in a service:
- `api/` — FastAPI routers; HTTP shape only; calls `app/*`
- `schema/` — Pydantic models for request/response validation
- `app/` — orchestration + business logic; calls `viberoi_shared.*`
- `tests/` — service-specific tests

## Scoping shared modules — domain, not primitive

```python
# Good:
from viberoi_shared.sessions import create
from viberoi_shared.orgs import get_by_domain
from viberoi_shared.notifications import enqueue

# Avoid:
from viberoi_shared.db import execute_sql      # primitive — invites SQL in services
from viberoi_shared.utils import do_thing      # vague — never name a module `utils`
```

Primitive-only wrappers turn the shared lib into a god object. Add domain-shaped functions; if it doesn't fit any existing domain, create a new domain module.

## Per-service file layout

```
backend/services/<name>/
  <name>/
    __init__.py
    main.py                   # FastAPI app entry
    api/
      __init__.py
      <router>.py             # APIRouter; thin
    schema/
      __init__.py
      requests.py             # Pydantic request models
      responses.py            # Pydantic response models
    app/
      __init__.py
      <feature>.py            # business logic; pure-ish functions
  tests/
    conftest.py
    test_<feature>.py
  pyproject.toml
  Dockerfile
```

## File and function size

Enforced via ruff:

- Max **400 lines** per file (hard cap 500). Split by domain when nearing.
- Max **50 lines** per function.
- Max **5 positional args**; past that, use a Pydantic model.
- Cyclomatic complexity **≤ 10**.
- Max nesting depth **4**.
- Max **20 imports** per module.

If you need to break a limit, justify in the PR — rare exceptions are acceptable.

## Code reuse — three-strikes rule

Same logic appears in two services? On the third write, it goes to `viberoi_shared`. No exceptions.

No copy-paste across modules. If you'd write the same loop, the same parser, the same retry logic twice — extract.

## No cross-service imports

Services import from `viberoi_shared` and stdlib only. They cannot import from `services/<other_service>/`. CI lint catches this.

If two services need the same code, it belongs in `viberoi_shared`.

## Type safety

- Every function signature typed. Ruff `ANN` rules.
- `mypy --strict` on `packages/shared/`.
- `mypy` (default) on `services/` and `lambdas/`.
- No `Any` outside parser boundaries. Comment why if unavoidable.
- Pydantic models at every boundary (HTTP, SQS, S3 envelopes, Cognito claims). No raw dicts crossing service boundaries.

## Async-first

- `async def` handlers everywhere.
- Async SQLAlchemy (`AsyncSession`).
- Async Redis (`redis.asyncio`).
- Async boto3 via `aioboto3`.
- All I/O has explicit timeouts. No unbounded `await`.
- Context managers for DB/Redis/S3 — `async with`, never "create then maybe close".

## Naming

- Modules: `snake_case`.
- Classes: `PascalCase`.
- Functions, variables: `snake_case`.
- Constants: `UPPER_SNAKE_CASE`.
- Private: leading underscore.
- Domain modules in shared: plural noun for collections (`sessions/`, `orgs/`, `tickets/`); singular for capabilities (`crypto/`, `logging/`).

## Adding a new service

See `docs/adding-a-service.md` for the checklist. In short:

1. Copy `backend/services/_template/` to `backend/services/<name>/`.
2. Update `pyproject.toml` (name, deps).
3. Add to root workspace members.
4. Add CI job (or workflow matrix entry).
5. Add Terraform module entry for the env.
6. Health endpoint + at least one feature test.
