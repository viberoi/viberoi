# infra/docker/

Dockerfile pattern for VibeROI Python services and Lambdas.

## The pattern

All Python services and Lambdas follow the same multi-stage shape:

1. **Builder** — installs uv, copies workspace manifests first (for layer caching), runs `uv sync --package <name>` so third-party deps cache separately from source changes.
2. **Runtime** — `python:3.12-slim`, non-root user, only the installed `.venv` plus the service source.

See `backend/services/ingest/Dockerfile` for the concrete reference. To add a new service, **copy it and change the package name + entry CMD** — no need to write Dockerfiles from scratch.

## Build context

Every Dockerfile expects to be built from the **repo root** (not the service directory). The build needs to see the workspace `pyproject.toml`, `uv.lock`, and all workspace packages:

```bash
# From repo root:
docker build -f backend/services/ingest/Dockerfile -t viberoi-ingest:dev .
```

## Lambdas

Lambda images use the same builder stage, but the runtime stage extends `public.ecr.aws/lambda/python:3.12` instead of `python:3.12-slim`. There's no uvicorn or port — the AWS Lambda runtime invokes the handler directly. Pattern lands with the first Lambda (Cognito PreSignUp, Slice 5).

## Why container Lambdas instead of ZIPs

So `viberoi_shared` is installed identically in ECS and Lambda — one build pipeline, one bug-fix path. See `.claude/rules/structure.md` for the rationale.

## Size budget

- Service runtime: < 200 MB target
- Lambda runtime: < 150 MB target (cold-start sensitive)

Slim base + multi-stage + `--no-install-recommends` keeps us there for most cases. Use `docker images` after building to verify.
