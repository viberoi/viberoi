# envs/dev

Dev environment composition. Up to and including Slice 6D — VPC,
data layer, Cognito, ECR, ECS cluster, IAM, 5 Fargate services
(desired_count=0), 4 container Lambdas, API Gateway → webhook receiver.

## Prerequisites

1. Bootstrap module applied — see `../../bootstrap/`.
2. AWS credentials configured (env vars or `~/.aws/credentials`).
3. Terraform >= 1.6, AWS provider 5.x.

## First-time init

The S3 backend `bucket` depends on your account id, so it's passed at
init time:

```powershell
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
terraform init -backend-config="bucket=viberoi-tf-state-$ACCOUNT_ID"
```

## Apply order

### Phase 1 — everything except Cognito triggers

```powershell
terraform plan -out=plan-phase1.tfplan
terraform apply plan-phase1.tfplan
```

After this finishes:
- VPC, RDS, Redis, S3, SQS, KMS, Secrets Manager exist.
- Cognito user pool exists, **no Lambda triggers wired**.
- ECS cluster, ECR repos, log groups, IAM roles exist.
- 5 ECS services exist with `desired_count = 0`.
- 4 Lambda functions exist with bootstrap image tag.
- API Gateway exists, routes wired.

### Phase 2 — push images, run DB bootstrap, wire Cognito triggers

1. Build + push container images (this happens in 6F via GitHub
   Actions; first time, do it manually):

   ```powershell
   $TAG = "first-deploy"
   # For each service / lambda, build from repo root + push to ECR.
   docker build -f backend/services/api/Dockerfile -t viberoi-dev-api:$TAG .
   docker tag viberoi-dev-api:$TAG <ecr-url>/viberoi-dev-api:$TAG
   docker push <ecr-url>/viberoi-dev-api:$TAG
   # … repeat for every repo …
   ```

2. Connect to RDS (via Session Manager tunnel or a temporary EC2)
   and run the role bootstrap SQL — see `../../modules/rds/README.md`.

3. Run Alembic migrations against the new RDS as `viberoi_admin`.

4. Edit `main.tf` — uncomment the three `lambda_*_arn` lines in the
   `module "cognito"` block and `terraform apply` again. This wires
   the PreSignUp / PostConfirmation / PreTokenGeneration triggers.

5. `aws ecs update-service --cluster <cluster> --service <service> --desired-count 1` for each ECS service.

### Phase 3 — paste webhook + Cognito hosted-UI URLs into provider config

The relevant outputs:
- `webhook_api_endpoint` — paste into GitHub/Jira/Linear webhook config
- `cognito_hosted_ui_domain` — frontend redirects users here for login

## Inputs

| variable | default | notes |
|---|---|---|
| `project` | `viberoi` | name prefix |
| `env` | `dev` | reflected in every resource name |
| `region` | `us-east-1` | locked |
| `vpc_cidr` | `10.20.0.0/16` | distinct per env |
| `az_count` | `2` | 3 for prod |
| `single_nat` | `true` | dev cost saver |
| `domain` | `""` | filled in 6E |
| `google_client_id` / `google_client_secret` | `""` | enables Google IdP when both set |
| `github_oidc_client_id` / `github_oidc_client_secret` | `""` | enables GitHub OIDC IdP |

## Outputs — what 6E / 6F consume

VPC: `vpc_id`, `public_subnet_ids`, `private_subnet_ids`, `data_subnet_ids`, all SG ids.
Crypto: `kms_key_arn`, `kms_alias_name`, `secret_arns`.
Data: `rds_endpoint`, `redis_primary_endpoint`, `org_data_bucket`,
`frontend_bucket`, `sqs_queue_arns`, `sqs_dlq_arns`.
Cognito: `cognito_user_pool_id`, `cognito_app_client_id`,
`cognito_hosted_ui_domain`.
Compute: `ecr_repository_urls`, `ecs_cluster_name`, `ecs_service_names`,
`lambda_function_names`, `webhook_api_endpoint`.
