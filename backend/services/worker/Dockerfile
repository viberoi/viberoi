# Worker service — multi-stage build.
# Build from REPO ROOT:
#   docker build -f backend/services/worker/Dockerfile -t viberoi-worker:dev .

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
COPY backend/services/worker/pyproject.toml backend/services/worker/

RUN uv sync --frozen --no-install-workspace --package viberoi-worker

COPY backend/packages/shared/ backend/packages/shared/
COPY backend/services/worker/ backend/services/worker/

RUN uv sync --frozen --package viberoi-worker

# ─── Stage 2: runtime ─────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r viberoi && useradd -r -g viberoi viberoi

WORKDIR /app

COPY --from=builder --chown=viberoi:viberoi /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER viberoi

# No port exposed — Worker is a pure SQS consumer.
# Healthcheck: ECS detects process exit; CloudWatch monitors SQS depth.
CMD ["python", "-m", "worker.main"]
