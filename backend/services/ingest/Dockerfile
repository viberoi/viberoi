# Ingest service — multi-stage build.
# Build from REPO ROOT, not this directory:
#   docker build -f backend/services/ingest/Dockerfile -t viberoi-ingest:dev .

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

# Copy workspace manifests first so the dep install layer caches independently
# of source changes.
COPY pyproject.toml uv.lock ./
COPY backend/packages/shared/pyproject.toml backend/packages/shared/
COPY backend/services/ingest/pyproject.toml backend/services/ingest/

# Install third-party deps only (workspace packages installed in the next step).
RUN uv sync --frozen --no-install-workspace --package viberoi-ingest

# Now copy actual source code and install the workspace packages.
COPY backend/packages/shared/ backend/packages/shared/
COPY backend/services/ingest/ backend/services/ingest/

RUN uv sync --frozen --package viberoi-ingest

# ─── Stage 2: runtime ─────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r viberoi && useradd -r -g viberoi viberoi

WORKDIR /app

# Bring over the resolved venv + source from the builder.
COPY --from=builder --chown=viberoi:viberoi /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER viberoi

EXPOSE 8000

# Healthcheck via Python stdlib — avoids pulling curl into the runtime image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/healthz').read()" || exit 1

CMD ["uvicorn", "ingest.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
