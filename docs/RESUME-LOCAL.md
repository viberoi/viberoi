# Resume work locally

After the AWS env is destroyed (Cognito + state bucket kept; all paid
resources gone), use this to spin local dev back up with **real Cognito
for auth + everything else local**.

## 1. Bring up local infra (~30s)

```powershell
./scripts/dev-up.ps1                  # Postgres + Redis + LocalStack
uv run alembic -c backend/migrations/alembic.ini upgrade head
uv run python scripts/seed-dev-data.py    # seed acme.test demo data
```

## 2. Bootstrap your real Cognito identity on local DB

```powershell
# Same sub Cognito issued you originally (lives in the real user pool):
uv run python scripts/bootstrap-cognito-user.py \
  --email adnankhan@rapyder.com \
  --sub 34c88428-b041-7060-2dfe-1d40b11df56b
```

## 3. Start backend services (3 terminals)

```powershell
# API service
uv run uvicorn api.main:app --port 8003 --reload --app-dir backend/services/api

# Ingest service
uv run uvicorn ingest.main:app --port 8004 --reload --app-dir backend/services/ingest

# Worker
uv run python -m worker.main
```

## 4. Start frontend

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173 — sign in via real Cognito Hosted UI, lands
on dashboard backed by local Postgres.

## 5. Run agent against your real Claude Code transcripts

```powershell
# Issue a fresh agent token for the OrgAdmin developer
uv run python scripts/issue-dev-token.py

# Register agent + push
.\agent\bin\viberoi-agent.exe register `
  --org-id 00000000-0000-0000-0000-000000000001 `
  --developer-id 00000000-0000-0000-0000-000000000101 `
  --token <pasted-from-above> `
  --url http://localhost:8004 `
  --claude-code-path "$env:USERPROFILE/.claude/projects"

.\agent\bin\viberoi-agent.exe push
```

## What's where now

| Service | Where | Cost |
|---|---|---|
| Auth (Cognito User Pool) | AWS real | $0 (free tier) |
| Frontend | localhost:5173 | $0 |
| API + Ingest + Worker | localhost | $0 |
| Postgres + Redis + LocalStack | docker-compose | $0 |
| Terraform state bucket + lock | AWS S3 + DynamoDB | ~$0.50/mo |
| ECR (image storage from earlier builds) | AWS | ~$0.50/mo |

Total monthly: **~$1**.

## When ready to redeploy

```powershell
cd infra/terraform/envs/dev
TF_VAR_domain="viberoi.io" TF_VAR_enable_cloudfront_custom_domain="true" `
  TF_VAR_enable_cognito_custom_domain="true" terraform apply
```

Then re-push images, re-run alembic against the new RDS, re-bootstrap
your user, and you're back. Cognito pool persisted so the sub is still
valid — no re-signup needed.

## Phase work to come (in priority order)

1. **Phase A — Stop the bleeding** (security holes)
   - Cognito Lambda triggers wiring (kills open self-signup)
   - Tighten dev passthrough (set `VIBEROI_ENV=staging` in cloud builds)
   - Start Razorpay merchant activation (calendar work)

2. **Phase B — Real users can sign up** (1 day)
   - PostConfirmation auto-creates org/dev row

3. **Phase C — Agent reports enough** (1-2 days)
   - machine_id_hash, /ingest/register, git enrichments

4. **Phase D — Dashboard shows real ROI** (3-4 days)
   - Worker computes the 12 stubbed KPIs
   - API endpoints for tool/ticket/cycle breakdowns
   - Frontend wires Insights + ROI + People pages

5. **Phase E — Integrations end-to-end** (3-4 days)
   - GitHub OAuth + webhook (Signals 2 + 5)
   - Jira OAuth + sprint sync (Signals 3 + 4)

6. **Phase F — Missing tool readers** (4-6 days, parallel-able)
   - Copilot (VS Code workspaceStorage + GH metrics API)
   - Kiro (S3 CSV + CUR)

7. **Phase G — Billing** (~3.5 weeks; Razorpay calendar gates it)
   - Schema, client, webhooks, GST, RBI e-mandate UX

See `docs/RUNBOOK-DEPLOY.md` for the full re-deploy steps.
