# Deploy runbook — VibeROI dev environment

End-to-end deploy of the dev environment to AWS. Cost ballpark: **~$80–110/mo
always-on** (NAT $32, RDS db.t4g.micro $13, ElastiCache cache.t4g.micro $11,
ALB $16, CloudFront ~$1, ECS Fargate task hours, S3/SQS/KMS pennies).

Prereqs already done:
- ✅ Bootstrap state bucket + lock table (commit `0a8d9ad`-ish, applied earlier)
- ✅ Cognito User Pool + SPA client + Hosted UI domain (applied `2cf8743`)
- ✅ All Dockerfiles + GitHub Actions workflows committed
- ✅ AWS CLI authenticated as `makemyitinerary` (admin in account 876611282878)
- ✅ Domain registered at Hostinger (DNS records added there, not Route 53)

## Phase 1 — apply full Terraform (~10 min)

Bring up VPC, RDS, ElastiCache, ALB, ECS, ECR, log groups, all IAM roles,
container Lambdas. ECS services come up at `desired_count=0` — they'll
stay there until images are pushed (Phase 3).

```powershell
cd infra/terraform/envs/dev

# Pass the apex domain so ACM module + ALB module activate.
$env:TF_VAR_domain = "viberoi.io"   # replace with your actual domain

terraform plan -out=phase1.tfplan
# Review the plan — should be ~80–90 resources to add.
terraform apply phase1.tfplan
```

After apply, capture the outputs:

```powershell
terraform output -json > ../../../docs/.deploy-outputs.json
```

Key values to note:
- `rds_endpoint` — needed for migration step
- `ecr_repository_urls` — needed for Phase 3
- `ecs_cluster_name` — needed for service redeploys
- `acm_validation_records` — paste these CNAMEs at Hostinger NOW
- `hostinger_dns_records_needed` — list of all CNAMEs to add
- `cognito_hosted_ui_domain` — won't change (already deployed)

## Phase 2 — Hostinger DNS (~5 min you + 30 min wait)

Add every CNAME from `terraform output acm_validation_records` plus:

| Hostinger CNAME | Points to |
|---|---|
| `api.viberoi.io` | (ALB DNS name from `terraform output alb_dns_name`) |
| `webhooks.viberoi.io` | (API Gateway endpoint from `webhook_api_endpoint`) |
| ACM `_xxxxx.viberoi.io` records | values from `acm_validation_records` |

(`app.viberoi.io` and `auth.viberoi.io` come in Phase 5 after the cert
validates — CloudFront and Cognito refuse pending certs.)

**Wait** ~30 min, then verify ACM cert validated:

```powershell
terraform output acm_certificate_status   # should be "ISSUED"
```

If it's still `PENDING_VALIDATION` after 1 hour, recheck DNS records
exactly match — case sensitive, no extra dots.

## Phase 3 — push Docker images (~15 min)

Two options:

**(a) Via GitHub Actions (recommended).** Push a commit to `main` that
touches `backend/**` (the build matrix triggers on path filter), or
manually dispatch `deploy-services.yml` from the Actions tab with
target=`all`. This builds all 5 services + 4 Lambdas in parallel and
pushes to ECR.

**(b) Locally (faster for one-off testing).** Log in to ECR then docker
push:

```powershell
aws ecr get-login-password --region us-east-1 |
  docker login --username AWS --password-stdin 876611282878.dkr.ecr.us-east-1.amazonaws.com

# Build + tag + push each service (replace <commit-sha> with `git rev-parse HEAD`)
$sha = git rev-parse --short HEAD
foreach ($svc in @("api","ingest","worker","integration","notification")) {
  docker build -f "backend/services/$svc/Dockerfile" `
    -t "876611282878.dkr.ecr.us-east-1.amazonaws.com/viberoi-dev-${svc}:$sha" `
    -t "876611282878.dkr.ecr.us-east-1.amazonaws.com/viberoi-dev-${svc}:latest" .
  docker push --all-tags "876611282878.dkr.ecr.us-east-1.amazonaws.com/viberoi-dev-$svc"
}
```

After images are in ECR, scale services up:

```powershell
$cluster = "viberoi-dev-ecs"
foreach ($svc in @("api","ingest","integration","notification")) {
  aws ecs update-service --cluster $cluster --service "viberoi-dev-$svc" `
    --desired-count 1 --force-new-deployment
}
# Worker doesn't need a target group; same command applies.
aws ecs update-service --cluster $cluster --service viberoi-dev-worker `
  --desired-count 1 --force-new-deployment
```

## Phase 4 — DB migrations against RDS (~3 min)

Tunnel from your laptop into the VPC (RDS isn't publicly accessible).
Easiest: temporarily open the RDS security group to your IP, run
`alembic upgrade head`, close it again. Or use a bastion EC2 / SSM
Session Manager.

```powershell
# Get your public IP
$myip = (Invoke-RestMethod ifconfig.me).Trim()

# Open RDS to your IP (REVERT THIS after migrations — don't leave open)
$sg = (terraform output -raw sg_rds)
aws ec2 authorize-security-group-ingress --group-id $sg `
  --protocol tcp --port 5432 --cidr "$myip/32"

$rds = (terraform output -raw rds_endpoint)
$env:VIBEROI_DATABASE_ADMIN_URL = "postgresql+psycopg://viberoi_admin:<password>@${rds}/viberoi"
# Get the password
$pwd_arn = (terraform output -json secret_arns | ConvertFrom-Json).rds_master_password
$pwd = (aws secretsmanager get-secret-value --secret-id $pwd_arn --query SecretString --output text)

uv run alembic -c backend/migrations/alembic.ini upgrade head

# Revoke
aws ec2 revoke-security-group-ingress --group-id $sg `
  --protocol tcp --port 5432 --cidr "$myip/32"
```

## Phase 5 — flip toggles + apply Phase 2 modules (~5 min)

After ACM is `ISSUED`:

```powershell
$env:TF_VAR_enable_cognito_custom_domain = "true"
$env:TF_VAR_enable_cloudfront_custom_domain = "true"

terraform plan -out=phase5.tfplan
terraform apply phase5.tfplan
```

Then add the remaining Hostinger CNAMEs:

| Hostinger CNAME | Points to |
|---|---|
| `app.viberoi.io` | `terraform output cloudfront_domain_name` |
| `auth.viberoi.io` | `terraform output cognito_custom_domain_target` |

## Phase 6 — frontend deploy (~5 min)

```powershell
cd frontend

# Update env to use the deployed URLs
$env:VITE_COGNITO_REDIRECT_URI = "https://app.viberoi.io/auth/callback"
$env:VITE_COGNITO_LOGOUT_URI = "https://app.viberoi.io/"

npm run build

# Sync to S3 + invalidate CloudFront
$bucket = (terraform output -raw frontend_bucket)
$dist = (terraform output -raw cloudfront_distribution_id)
aws s3 sync dist/ s3://$bucket/ --delete
aws cloudfront create-invalidation --distribution-id $dist --paths "/*"
```

Also update Cognito callback URLs (currently localhost-only):

```powershell
# Edit infra/terraform/envs/dev/main.tf line ~152:
#   callback_urls = ["https://app.viberoi.io/auth/callback", ...]
#   logout_urls   = ["https://app.viberoi.io/", ...]
# Then:
terraform apply
```

## Phase 7 — smoke test (~10 min)

1. Open `https://app.viberoi.io` — Cognito Hosted UI redirect should work.
2. Sign in as your existing user (`adnankhan@rapyder.com`).
3. **Note: dashboard will be empty** — the DB is fresh on RDS. Re-run
   the agent against your transcripts pointed at the deployed ingest:
   ```powershell
   .\agent\bin\viberoi-agent.exe register `
     --org-id 7f2050dc-3a23-40ba-a91f-2dc4f0309854 `
     --developer-id <new-dev-id-from-bootstrap-script-against-RDS> `
     --token <new-org-token-from-issue-dev-token> `
     --url https://api.viberoi.io `
     --claude-code-path "$env:USERPROFILE/.claude/projects"
   .\agent\bin\viberoi-agent.exe push
   ```
4. Verify Sessions list populates, KPI snapshot reflects real numbers.

## Rollback

If anything goes wrong mid-deploy:

```powershell
# Scale services back to 0 (stops Fargate charges)
foreach ($svc in @("api","ingest","worker","integration","notification")) {
  aws ecs update-service --cluster viberoi-dev-ecs `
    --service "viberoi-dev-$svc" --desired-count 0
}

# Or destroy the whole dev env (preserves Cognito + bootstrap state)
terraform destroy -target=module.alb -target=module.rds -target=module.redis `
                  -target=module.ecs_api -target=module.ecs_ingest `
                  -target=module.ecs_worker -target=module.ecs_integration `
                  -target=module.ecs_notification
```

## Always-on cost breakdown

| Resource | $/mo |
|---|---|
| NAT Gateway (single AZ) | ~$32 |
| RDS db.t4g.micro | ~$13 |
| ElastiCache cache.t4g.micro | ~$11 |
| ALB | ~$16 |
| ECS Fargate (5 services × 0.25 vCPU × 0.5GB × 24/7) | ~$25 |
| CloudFront | ~$1 |
| S3 + KMS + SQS + Secrets Manager | ~$2 |
| Cognito | $0 (free under 50k MAU) |
| ECR storage | ~$0.50 |
| **Total** | **~$100/mo** |

To cut roughly in half: scale ECS services to 0 when not actively
testing (still pay NAT + RDS + Redis + ALB which is the floor).
