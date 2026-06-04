# Terraform via GitHub Actions

Terraform `plan` and `apply` run in GitHub Actions, **not** from your
laptop. AWS credentials are short-lived (15 min) OIDC tokens — no
long-lived secrets stored in GitHub.

## What's set up

| Resource | Value |
|---|---|
| OIDC provider | `arn:aws:iam::876611282878:oidc-provider/token.actions.githubusercontent.com` |
| IAM role | `arn:aws:iam::876611282878:role/viberoi-github-actions-terraform` |
| Attached policy | `AdministratorAccess` (dev — scope down for prod) |
| Trust scope | `repo:viberoi/viberoi:ref:refs/heads/main` only |
| Workflow | `.github/workflows/terraform-dev.yml` |

## One-time GitHub setup

Before the first apply, create the GitHub Environments that gate it.
**Settings → Environments → New environment**:

| Environment | Required reviewers | Purpose |
|---|---|---|
| `aws-dev` | Add yourself (or a small list) | Gates `apply` |
| `aws-dev-destroy` | Add yourself | Gates `destroy` (separate so you can't fat-finger the wrong choice) |

Without reviewers, the workflow runs without prompting. Add at least
one reviewer per environment for the manual-approval gate to kick in.

## Workflow triggers

| Event | What runs |
|---|---|
| Push to `main` touching `infra/terraform/**` | `plan` (auto). Artifact uploaded; summary in the run page. |
| Workflow dispatch, action = `plan` | `plan` only. |
| Workflow dispatch, action = `apply` | `plan` → wait for `aws-dev` approval → `apply` the artifact. |
| Workflow dispatch, action = `destroy` | `destroy` only, gated by `aws-dev-destroy`. |

## Running it

### Auto-plan on every change

Just push to `main`. The workflow runs, plan summary appears in
**Actions → terraform-dev → <run> → Summary**. Plan artifact (`tfplan-<run_id>`)
is uploaded.

### Manual apply

1. **Actions** tab → **terraform-dev** → **Run workflow**.
2. Pick the branch (`main`) + action = `apply`.
3. Click **Run workflow**.
4. The `plan` job runs, then `apply` waits for approval. You'll get
   an email + GitHub notification.
5. Open the run, click **Review deployments**, approve.
6. `apply` runs. Outputs render in the run summary.

### Manual destroy

Same as apply but action = `destroy`. Gated by `aws-dev-destroy`.

## What the workflow does, step by step

`plan`:
- Configure AWS via OIDC (assume the role above).
- `terraform fmt -check -recursive` — fails the run if anything is
  unformatted.
- `terraform validate`.
- `terraform plan -out=tfplan`.
- Render plan to `$GITHUB_STEP_SUMMARY`.
- Upload `tfplan` as an artifact for the `apply` job.

`apply`:
- Download the plan artifact from the same run.
- `terraform apply` the exact plan — no replanning. Guarantees the
  apply matches what was reviewed.

## When to update

- The role + provider are one-time. Don't re-create.
- If you ever want PR plans (without apply rights), create a second
  IAM role with `repo:viberoi/viberoi:pull_request` trust and only
  `ReadOnlyAccess` + `AWSReadOnlyAccess`. Wire a separate workflow
  on PR triggers.
- For staging / prod, repeat the OIDC role creation with stricter
  trust (e.g. `ref:refs/heads/staging`) and a custom least-privilege
  policy instead of `AdministratorAccess`.

## Costs

GitHub Actions: free under the 2,000 min/month tier on private repos.
Each terraform run is ~2-5 min, so ~400 runs/month free.
