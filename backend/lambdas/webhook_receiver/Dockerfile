# Webhook receiver Lambda — container image.
# Build from REPO ROOT:
#   docker build -f backend/lambdas/webhook_receiver/Dockerfile -t viberoi-webhook-receiver:dev .

# ─── Stage 1: builder ──────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.4 /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY backend/packages/shared/pyproject.toml backend/packages/shared/
COPY backend/lambdas/webhook_receiver/pyproject.toml backend/lambdas/webhook_receiver/

RUN uv sync --frozen --no-install-workspace --package viberoi-webhook-receiver

COPY backend/packages/shared/ backend/packages/shared/
COPY backend/lambdas/webhook_receiver/ backend/lambdas/webhook_receiver/

RUN uv sync --frozen --package viberoi-webhook-receiver

# ─── Stage 2: Lambda runtime ──────────────────────────────────────────────
# AWS Lambda's official base image — provides the Runtime Interface Client
# that invokes our handler.
FROM public.ecr.aws/lambda/python:3.12

# Copy the installed venv from the builder into the Lambda task root.
COPY --from=builder /app/.venv/lib/python3.12/site-packages ${LAMBDA_TASK_ROOT}

# Copy the handler module.
COPY --from=builder /app/backend/lambdas/webhook_receiver/webhook_receiver ${LAMBDA_TASK_ROOT}/webhook_receiver

# Lambda Runtime Interface invokes "<module>.<function>" — our handler.
CMD ["webhook_receiver.handler.handler"]
