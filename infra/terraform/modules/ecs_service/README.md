# ecs_service

Reusable Fargate service. One invocation per backend service.

## Inputs

| name | notes |
|---|---|
| `service_name` | short name — drives task family + log group lookup |
| `image_uri` | full URI including tag |
| `execution_role_arn` / `task_role_arn` | from modules/iam_task_role |
| `log_group_name` | from modules/log_groups |
| `container_port` | 0 for pure consumers (no port published) |
| `cpu` / `memory` | 256 / 512 default (0.25 vCPU) |
| `desired_count` | 0 default so first apply doesn't fail on missing image |
| `env_vars` | plaintext map |
| `secrets` | map env-var → Secrets Manager ARN |
| `load_balancer` | `{target_group_arn, container_port}` or null |
| `command` | override CMD if needed |

## Lifecycle behaviour

`task_definition` and `desired_count` are in `lifecycle.ignore_changes`
so Terraform doesn't fight the deploy pipeline. The pipeline updates
both directly via `aws ecs update-service`.

## Outputs

`service_name`, `task_definition_family`, `task_definition_arn`.
