# Cognito PreSignUp Lambda — container image.
# Build from REPO ROOT:
#   docker build -f backend/lambdas/cognito_presignup/Dockerfile -t viberoi-cognito-presignup:dev .

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
COPY backend/lambdas/cognito_presignup/pyproject.toml backend/lambdas/cognito_presignup/

RUN uv sync --frozen --no-install-workspace --package viberoi-cognito-presignup

COPY backend/packages/shared/ backend/packages/shared/
COPY backend/lambdas/cognito_presignup/ backend/lambdas/cognito_presignup/

RUN uv sync --frozen --package viberoi-cognito-presignup

# ─── Stage 2: Lambda runtime ──────────────────────────────────────────────
FROM public.ecr.aws/lambda/python:3.12

COPY --from=builder /app/.venv/lib/python3.12/site-packages ${LAMBDA_TASK_ROOT}
COPY --from=builder /app/backend/lambdas/cognito_presignup/cognito_presignup ${LAMBDA_TASK_ROOT}/cognito_presignup

CMD ["cognito_presignup.handler.handler"]
