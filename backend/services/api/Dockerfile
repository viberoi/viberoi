# API service — multi-stage build.
# Build from REPO ROOT:
#   docker build -f backend/services/api/Dockerfile -t viberoi-api:dev .

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
COPY backend/services/api/pyproject.toml backend/services/api/

RUN uv sync --frozen --no-install-workspace --package viberoi-api

COPY backend/packages/shared/ backend/packages/shared/
COPY backend/services/api/ backend/services/api/

RUN uv sync --frozen --package viberoi-api

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
EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8003/healthz').read()" || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "2"]
