#!/usr/bin/env bash
# Bring up local infra: Postgres + Redis + LocalStack.
# Idempotent — safe to run repeatedly.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "Starting VibeROI local infra..."
docker compose up -d

echo
echo "Waiting for services to be healthy..."
timeout=90
elapsed=0
while [ "$elapsed" -lt "$timeout" ]; do
    sleep 3
    elapsed=$((elapsed + 3))
    if ! docker compose ps --format json 2>/dev/null \
        | jq -e 'select(.Health and .Health != "healthy")' >/dev/null 2>&1; then
        break
    fi
    echo "  ... waiting (${elapsed}s)"
done

echo
echo "Status:"
docker compose ps

cat <<EOF

Postgres:   localhost:5432  (user: viberoi, password: viberoi, db: viberoi)
Redis:      localhost:6379
LocalStack: localhost:4566  (S3, SQS, KMS, Secrets Manager)

Next:
  uv sync
  uv run alembic upgrade head    # once migrations exist
  uv run pytest

EOF
