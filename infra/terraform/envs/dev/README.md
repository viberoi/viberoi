# envs/dev

Dev environment composition. Through Slice 6E — full edge layer.

## Prerequisites

1. Bootstrap module applied. State bucket + lock table exist.
2. AWS credentials configured.
3. Terraform >= 1.6, AWS provider 5.x.
4. (Optional, for 6E) Domain managed at Hostinger (or wherever).

## First-time init

```powershell
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
terraform init -backend-config="bucket=viberoi-tf-state-$ACCOUNT_ID"
```

## Apply timeline — first deployment

### Phase 1 — base infra (no domain yet)

```powershell
terraform plan -out=phase1.tfplan
terraform apply phase1.tfplan
```

You get: VPC, RDS, Redis, S3, SQS, KMS, Secrets Manager, Cognito user
pool, ECR repos, ECS cluster, log groups, IAM roles, 5 ECS services
at `desired_count=0`, 4 Lambdas with bootstrap image, API Gateway.

No ALB, no CloudFront-with-domain, no Cognito custom domain — those
need a cert that needs a domain.

### Phase 2 — push images, bootstrap DB

1. Build + push every service / lambda image to ECR (manual first
   time; GitHub Actions in 6F).
2. Connect to RDS (Session Manager tunnel) and run the role bootstrap
   SQL from `modules/rds/README.md`.
3. Run `alembic upgrade head` against the new RDS.

### Phase 3 — domain wiring (6E)

1. Set `domain` in `dev.auto.tfvars` (or `TF_VAR_domain`):

   ```hcl
   domain = "viberoi.io"
   ```

2. `terraform apply` — creates the ACM cert, ALB, ALB target groups,
   listener rules, CloudFront (still on default `.cloudfront.net`),
   wires ECS services to their TGs.

3. Read the output:

   ```powershell
   terraform output -json acm_validation_records
   terraform output hostinger_dns_records_needed
   ```

   Add **every** CNAME shown to Hostinger:
   - One per ACM validation entry (apex + 4 SANs = 5 CNAMEs).
   - `api.<domain>` → `<alb_dns_name>`.
   - `webhooks.<domain>` → `<api_gateway_endpoint>`.

4. Wait ~30 minutes. AWS validates ACM. Confirm:

   ```powershell
   terraform refresh
   terraform output acm_certificate_status
   # → ISSUED
   ```

5. Flip the Phase 3 toggles in tfvars:

   ```hcl
   enable_cloudfront_custom_domain = true
   enable_cognito_custom_domain    = true
   ```

   `terraform apply` again. Add the last two CNAMEs from the output:
   - `app.<domain>` → CloudFront distribution domain.
   - `auth.<domain>` → Cognito's CloudFront target.

6. Edit `main.tf` to wire the Cognito triggers (uncomment the three
   `lambda_*_arn` lines in `module "cognito"`). `terraform apply`.

7. `aws ecs update-service --cluster <cluster> --service <service> --desired-count 1`
   for each ECS service.

### Phase 4 — login test

Visit `https://app.<domain>` → Cognito hosted UI at `auth.<domain>`
→ email/OTP → land on dashboard. The frontend calls `https://api.<domain>`.

## Inputs

| variable | default | notes |
|---|---|---|
| `project` | `viberoi` | name prefix |
| `env` | `dev` | reflected in every resource name |
| `region` | `us-east-1` | locked |
| `vpc_cidr` | `10.20.0.0/16` | distinct per env |
| `az_count` | `2` | 3 for prod |
| `single_nat` | `true` | dev cost saver |
| `domain` | `""` | apex. Empty disables all 6E |
| `enable_cognito_custom_domain` | `false` | Phase 3 — flip when cert is ISSUED |
| `enable_cloudfront_custom_domain` | `false` | Phase 3 — same rule |
| `google_client_id` / `google_client_secret` | `""` | enables Google IdP |
| `github_oidc_client_id` / `github_oidc_client_secret` | `""` | enables GitHub OIDC |

## Outputs — what 6F + the deploy pipeline consume

VPC + crypto + data: `vpc_id`, `kms_key_arn`, `rds_endpoint`,
`redis_primary_endpoint`, `org_data_bucket`, `frontend_bucket`,
`sqs_queue_arns`, `sqs_dlq_arns`, `secret_arns`.

Cognito: `cognito_user_pool_id`, `cognito_app_client_id`,
`cognito_hosted_ui_domain`, `cognito_custom_domain_target` (when set).

Compute: `ecr_repository_urls`, `ecs_cluster_name`, `ecs_service_names`,
`lambda_function_names`, `webhook_api_endpoint`.

Edge: `acm_certificate_arn`, `acm_validation_records`,
`acm_certificate_status`, `alb_dns_name`, `cloudfront_domain_name`,
`cloudfront_distribution_id`, `hostinger_dns_records_needed`.
