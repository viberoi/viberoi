# Terraform bootstrap

Creates the **state bucket + lock table** that the rest of Terraform uses for remote state. Apply once per AWS account.

## When

- Brand-new AWS account (first time ever)
- Resetting state infrastructure (rare)

## How (one-time apply)

```bash
cd infra/terraform/bootstrap

# Set your account ID from the AWS CLI
export TF_VAR_account_id=$(aws sts get-caller-identity --query Account --output text)

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

## After apply

The output `backend_config_snippet` shows the exact `terraform { backend "s3" { ... } }` block to paste into every other module's `backend.tf`. Subsequent `terraform init` in those modules wires them to the remote state.

## Why local state here

Chicken-and-egg: the bucket that holds remote state has to exist before you can use remote state. This module creates the bucket; its own state stays local (`terraform.tfstate` in this directory — gitignored, never commit).

You can optionally migrate this module's own state into the bucket after creation (`terraform init -migrate-state`), but it's rarely worth the operational complexity for a one-time module.

## Resources created

| Resource | Name | Purpose |
|---|---|---|
| S3 bucket | `viberoi-tf-state-<account_id>` | Holds `.tfstate` files for all other modules |
| Bucket versioning | enabled | Roll back accidental state corruption |
| Bucket encryption | AES256 SSE | Encrypted at rest |
| Public access block | all denied | State must never be public |
| DynamoDB table | `viberoi-tf-lock` | Prevents concurrent `terraform apply` operations |
| DynamoDB PITR | enabled | Recover lock state if needed |

## Cost

- S3 storage: a few KB per state file → cents per month
- DynamoDB: pay-per-request, ~free for normal Terraform usage
- Total: under $1/month for the whole bootstrap stack
