# envs/dev

Dev environment composition.

## Prerequisites

1. Bootstrap module applied. The S3 state bucket and DynamoDB lock
   table from `../../bootstrap/` must exist.
2. AWS credentials configured (env vars or `~/.aws/credentials`).
3. Terraform >= 1.6, AWS provider 5.x.

## First-time init

The S3 backend `bucket` name depends on your AWS account id, so it's
passed at init time instead of hardcoded:

```powershell
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
terraform init -backend-config="bucket=viberoi-tf-state-$ACCOUNT_ID"
```

## Planning

```powershell
terraform plan
```

The current Slice 6A scope creates **VPC + subnets + NAT + base security
groups only**. Cost: ~$32/mo for the single NAT gateway. RDS, ECS,
Redis, Cognito, ALB land in subsequent sub-batches and bring real cost
when applied.

## Inputs

| variable | default | notes |
|---|---|---|
| `project` | `viberoi` | name prefix |
| `env` | `dev` | reflected in every resource name |
| `region` | `us-east-1` | locked region |
| `vpc_cidr` | `10.20.0.0/16` | bump per env if you want distinct CIDRs |
| `az_count` | `2` | 3 for prod durability |
| `single_nat` | `true` | dev cost saver; flip in prod |
| `domain` | `""` | filled in 6E |

## Outputs

`account_id`, `vpc_id`, `public_subnet_ids`, `private_subnet_ids`,
`data_subnet_ids`, `sg_alb`, `sg_services`, `sg_lambda`, `sg_rds`,
`sg_redis`. These are the wire that subsequent sub-batches plug into.
