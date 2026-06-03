# container_lambda

Lambda function backed by an ECR image.

Used by: webhook_receiver, cognito_presignup, cognito_postconfirm,
cognito_pre_token_generation.

## Inputs

| name | notes |
|---|---|
| `image_uri` | full ECR URI including tag |
| `role_arn` | from modules/iam_task_role (assume_role_service=lambda.amazonaws.com) |
| `vpc_subnet_ids` | empty = no VPC. Set to private_subnet_ids for DB access. |
| `vpc_security_group_ids` | required if vpc_subnet_ids is set |
| `env_vars` | plaintext map. COGNITO_USER_POOL_ID lives here. |
| `timeout_seconds` | default 30 |
| `memory_mb` | default 512 |
| `log_group_name` | optional — pass from modules/log_groups for consistency |

## VPC attach

The webhook receiver needs DB access (decrypt webhook secret), so VPC
attach is on. Cognito triggers also need DB access for org/developer
creation, so they attach too. The PreTokenGeneration trigger could
skip VPC attach (no DB call needed), but consistency wins.

## Outputs

`function_name`, `function_arn`, `invoke_arn` (the API Gateway form).
