# alb

Public ALB with one HTTPS listener + per-service path-based routing.

## Default routing

| Path | → Service | Port |
|---|---|---|
| `/ingest/*`, `/agent/*` | ingest | 8001 |
| `/integrations/*` | integration | 8002 |
| everything else (default) | api | 8003 |

Override via the `services` variable. The service whose `path_patterns`
is `["*"]` becomes the listener's default action AND the highest-priority
rule.

## TLS

- TLS policy: `ELBSecurityPolicy-TLS13-1-2-2021-06`.
- Cert from `modules/acm_cert`. ALB tolerates a pending cert — HTTPS
  serves once validation completes.

## Health checks

Each TG hits `/healthz` (`200` matcher), every 30s. 2 healthy = up,
3 unhealthy = down.

## Inputs

| name | notes |
|---|---|
| `vpc_id` | from modules/vpc |
| `subnet_ids` | public subnets |
| `security_group_ids` | `[modules/security_groups.alb_id]` |
| `certificate_arn` | from modules/acm_cert |
| `services` | map service → `{container_port, health_path, path_patterns, priority}` |

## Outputs

`alb_dns_name`, `alb_arn`, `alb_zone_id`, `target_group_arns`,
`https_listener_arn`.
