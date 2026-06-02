# VibeROI — Architecture Overview

This document is a pointer + 1-page mental model. The authoritative architecture lives in `frontend/VibeROI-DataSource-Master-final.md` (locked decisions, sealed) along with the BRD and FSD.

## Authoritative sources

| Topic | Source |
|---|---|
| Product, personas, business goals | [`BRD-v1.0.md`](../BRD-v1.0.md) |
| Functional spec, screens, flows, RBAC | [`FSD-v1.0-final.md`](../FSD-v1.0-final.md) |
| Tool data sources, session schema, attribution engine, cloud deployment, agent design, API surface, pricing | [`frontend/VibeROI-DataSource-Master-final.md`](../frontend/VibeROI-DataSource-Master-final.md) |

Don't relitigate sealed decisions without a clear reason. If a decision needs to change, amend the source doc *and* note the amendment in the memory/security/structure files.

## 1-page mental model

```
Developer machine                AWS us-east-1                        Browser
─────────────────                ──────────────────────────────       ──────────
Go agent ───────HTTPS───────►  ALB ──► Ingest Service ──► S3 raw       React SPA
(fsnotify +                                                    │       (Vite +
 60s polling)                                                  ▼       Tremor +
                                                          SQS session   TanStack)
                                                              │            ▲
GitHub / Jira / Linear ─webhooks─► API Gateway ─► Webhook         │            │
                                                Lambda                │            │
                                                    │                 ▼            │
                                                    └──► SQS webhooks ─► Worker Service
                                                                             │
                                                                             ▼
                                                          RDS Postgres (RLS)
                                                          ElastiCache Redis  ─► SSE ─► API Service ─► CloudFront
                                                                             ▲
                                                                  Integration Service
                                                                  Notification Service
                                                                  Auth Service (Cognito orchestration)
                                                                  EventBridge crons → Worker
```

## Services (locked — Q-Final architecture)

| # | Service | Owns | SQS queue(s) |
|---|---|---|---|
| 1 | **Ingest** | Agent validation, S3 write, developer profile creation | — (writes to S3) |
| 2 | **API** | Dashboard HTTP, KPI endpoints, onboarding orchestration, SSE | — |
| 3 | **Auth** | Cognito orchestration, invitations, RBAC, role writes | — |
| 4 | **Worker** | Attribution engine, session processing, KPI writes, Redis | `session_ingest`, `backfill_jobs` |
| 5 | **Integration** | All external API calls (Jira/Linear/GitHub/Kiro/Copilot), OAuth tokens | — |
| 6 | **Notification** | All message delivery (Slack/Teams/Email/Chat) | `notification_jobs` |
| L | **Webhook Lambda** | HMAC verify per provider → SQS push | — |
| L | **Cognito Lambdas** | PreSignUp (domain lock), PostConfirmation (org/dev create) | — |
| L | **EventBridge crons** | Scheduled triggers → Worker via SQS | various |

## Data flow — happy path (session ingest)

1. Agent detects session end (inactivity >10 min)
2. Agent builds session object (locked schema v1.0), gzips, HMAC-signs, POSTs to `/ingest/session`
3. **Ingest Service** validates HMAC + `org_token`, writes raw to S3 `orgs/{org_id}/sessions/{date}/{session}.json.gz`
4. S3 event → SQS `session_ingest`
5. **Worker Service** picks up: runs Signals 1/3/4/5 attribution, writes to Postgres `sessions` (with RLS), increments Redis counters
6. Redis pub/sub → SSE to dashboard → live counters update without page reload
7. Hourly cron: KPI snapshot rebuild
8. Backfill cron (5 min): for `reconciled=false` rows, query Jira/Linear via Integration Service, recompute attribution

See `frontend/VibeROI-DataSource-Master-final.md` §Q14 for the canonical flow including PR webhook trigger and DLQ handling.

## Session object schema

Locked at v1.0 — defined in `backend/packages/shared/viberoi_shared/types/session.py` (`Session` class). Mirror in Go at `agent/pkg/schema`. Bump `schema_version` for any change.

Canonical source: `frontend/VibeROI-DataSource-Master-final.md` § "SESSION OBJECT SCHEMA — LOCKED".

## Attribution engine

5 signals + modifiers, computed in Worker Service:

1. Branch parse (35%) — regex on branch name
2. File overlap (20%, sprint-cohesion adjusted) — files∩ticketPRfiles
3. Temporal proximity (15%) — session active during ticket "In Progress"
4. Developer match (10%) — session.developer = ticket.assignee
5. Explicit mention (20%) — regex on commit messages + PR title

Modifiers: sprint cohesion, ticket criticality, dominant ticket.

Thresholds:
- ≥ 0.80 → auto-attribute
- 0.50–0.79 → WATCH flag
- < 0.50 → unattributed → unknown queue

Canonical source: `frontend/VibeROI-DataSource-Master-final.md` § Q5.

## Privacy guarantees (the product promise)

- Never store prompts, code, diffs, PR/issue/commit-message bodies
- All transport TLS 1.3
- All `org_token` storage Argon2id-hashed
- All PII at rest KMS+AES-256-GCM encrypted (envelope + rotation)
- All requests org-scoped via RLS — even bugs in app code can't leak cross-org data

See [`.claude/rules/security.md`](../.claude/rules/security.md).

## Local dev architecture

docker-compose brings up:

- Postgres 16 (with RLS enabled, `app.current_org_id` GUC initialized)
- Redis 7
- LocalStack (S3, SQS, KMS — covers prod AWS surface for dev/test)

Scripts in `scripts/` start/stop the stack and seed dev data.

## Deployment shape (production)

Per `frontend/VibeROI-DataSource-Master-final.md` § Q9 + § Q-Final:

- AWS us-east-1, single region for V1
- ECS Fargate for all 6 services (auto-scaled by SQS depth + CPU)
- Lambdas as container images (same Dockerfile base as services)
- RDS Postgres Multi-AZ + RLS
- ElastiCache Redis (cluster mode off for V1)
- CloudFront + S3 for React SPA
- API Gateway for webhook ingress
- EventBridge for scheduled triggers
- Secrets Manager for all credentials; IAM roles for service-to-service

Infrastructure cost estimate at MVP scale (~10 orgs, 100 devs): ~$131/month. See sealed doc for the breakdown.
