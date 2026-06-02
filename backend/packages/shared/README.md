# viberoi-shared

The shared library. Every service and Lambda consumes it. **No service writes raw SQL, opens a DB/Redis connection, calls KMS, calls boto3 for messaging, or instantiates a logger.** All of that lives here.

See [`../../../.claude/rules/structure.md`](../../../.claude/rules/structure.md) for the rule and [`../../../.claude/rules/security.md`](../../../.claude/rules/security.md) for the crypto/auth surface this module owns.

## Domain modules

- `db/` — async engine, org-scoped session factory, RLS context
- `sessions/` — CRUD + ORM for the locked session schema (v1.0)
- `tickets/` — CRUD + ORM for tickets, sprints
- `orgs/` — CRUD + ORM for orgs, developers, RBAC writes
- `kpis/` — snapshot read/write
- `redis/` — adapter + pub/sub + namespacing
- `sqs/` — publish/consume helpers + DLQ-aware retry
- `s3/` — raw-landing read/write
- `cognito/` — JWT validation + JWKS cache
- `crypto/` — Argon2id hashing + KMS envelope encryption (AES-256-GCM)
- `notifications/` — `enqueue()` only; delivery is Notification Service
- `webhooks/` — HMAC verification per provider
- `lambda_auth/` — per-trigger Lambda authentication checks
- `aws/` — boto3/aioboto3 client factories (so services never import boto3)
- `secrets/` — Secrets Manager wrapper, local-dev override
- `logging/` — structlog config + request_id middleware + PII scrubbing
- `errors/` — typed exceptions + FastAPI handlers
- `types/` — Pydantic models shared across services (Session, KPI structs, RBAC enums)
- `config/` — pydantic-settings loader

## Adding a new domain module

1. Create `viberoi_shared/<domain>/__init__.py` with the public API.
2. Implementation files alongside (`repository.py`, `models.py`, `service.py` etc.).
3. Tests in `tests/<domain>/`.
4. Re-export the public API from `__init__.py`.
5. Bump version in `pyproject.toml`.
