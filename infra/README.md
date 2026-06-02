# infra/

Terraform + Dockerfiles for VibeROI. Deploys backend services, Lambdas, the frontend (CloudFront + S3), and the agent's update/install endpoints.

## Layout

```
infra/
  docker/                          Dockerfile pattern + base layer docs
  terraform/
    bootstrap/                     ONE-TIME: state bucket + lock table
    modules/                       Reusable: vpc, rds, redis, ecs-service, lambda, cognito (Slice 2+)
    envs/{dev,staging,prod}/       Per-env wiring (Slice 2+)
```

## First-time setup (per AWS account)

1. Apply `terraform/bootstrap/` once — creates the S3 state bucket and DynamoDB lock table. See `terraform/bootstrap/README.md`.
2. Copy the output `backend_config_snippet` into every other module's `backend.tf`.
3. Apply the dev env, then staging, then prod.

## Slice 1 status

This slice ships only:
- `terraform/bootstrap/` — state bucket + lock table
- `docker/README.md` — the Dockerfile pattern, with `backend/services/ingest/Dockerfile` as the concrete example

VPC / RDS / Redis / Cognito / ECS service / Lambda modules land as services come online (Slice 2+).
