# Cognito PostConfirmation Lambda — container image.
# Build from REPO ROOT:
#   docker build -f backend/lambdas/cognito_postconfirm/Dockerfile -t viberoi-cognito-postconfirm:dev .

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
COPY backend/lambdas/cognito_postconfirm/pyproject.toml backend/lambdas/cognito_postconfirm/

RUN uv sync --frozen --no-install-workspace --package viberoi-cognito-postconfirm

COPY backend/packages/shared/ backend/packages/shared/
COPY backend/lambdas/cognito_postconfirm/ backend/lambdas/cognito_postconfirm/

RUN uv sync --frozen --package viberoi-cognito-postconfirm

FROM public.ecr.aws/lambda/python:3.12

COPY --from=builder /app/.venv/lib/python3.12/site-packages ${LAMBDA_TASK_ROOT}
COPY --from=builder /app/backend/lambdas/cognito_postconfirm/cognito_postconfirm ${LAMBDA_TASK_ROOT}/cognito_postconfirm

CMD ["cognito_postconfirm.handler.handler"]
