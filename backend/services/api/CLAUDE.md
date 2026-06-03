# CLAUDE.md — api service

Read-only dashboard backend. Every request:

1. Cognito JWT verification via `viberoi_shared.cognito.verify_jwt`
2. RLS-scoped DB access via `viberoi_shared.db.org_scoped_session(ctx.org_id)`
3. Shared repository helpers — never raw SQL

No mutations. No webhooks. No SQS publish. No outbound HTTP to external
providers (those live in `services/integration/`).

## Endpoint surface (Slice 5B)

| Method | Path | Auth | What |
|---|---|---|---|
| `GET` | `/healthz`, `/readyz` | none | probes |
| `GET` | `/sessions` | any role | paginated list of org's sessions with attribution + cost |
| `GET` | `/sessions/{id}` | any role | single session detail (metadata only) |
| `GET` | `/sprints` | any role | active + recent sprints with ticket counts |
| `GET` | `/sprints/{id}` | any role | sprint detail + attributed sessions/cost |
| `GET` | `/tickets/{id}` | any role | ticket detail + attributed sessions |
| `GET` | `/kpis/snapshot` | any role | org-level KPI rollup (cost, hours saved, hallucination rate) |
| `GET` | `/developers/me` | any role | the caller's own profile |

All `any role` endpoints accept OrgAdmin, TeamLead, Developer. Per-row
filtering (a Developer should only see their own sessions, a TeamLead
only their team's) is enforced inside the repository helpers using the
caller's `developer_id` / `team_id` — not by separate routes.

## Why no team-scoping in routes

The locked architecture keeps the URL space org-scoped and applies the
team/developer filter inside the repository, so the URL doesn't leak
the role hierarchy and `/sessions` is the same endpoint for all three
roles. The repository function takes `viewer_role`, `viewer_developer_id`,
`viewer_team_id` and decides what subset of the org's data is visible.

## Pagination

Cursor-based (NOT offset). Cursor = base64-encoded `(created_at, id)`
tuple. Stable across inserts; cheap on indexed scans. Page size 50,
hard cap 200.

## Rules that apply

- Never write raw SQL — use `viberoi_shared.sessions`, `viberoi_shared.tickets`, `viberoi_shared.kpis`.
- Always set RLS context via `org_scoped_session(ctx.org_id)`.
- Never log session/ticket bodies, emails, or any captured user content.
- Cognito JWT is required on every non-probe route — `dependency_overrides[authenticate]` in tests.
