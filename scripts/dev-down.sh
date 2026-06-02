#!/usr/bin/env bash
# Stop the local infra. Volumes persist by default.
# To wipe all data: docker compose down -v

set -euo pipefail
cd "$(dirname "$0")/.."

echo "Stopping VibeROI local infra..."
docker compose down
echo "Done. Volumes preserved. Wipe with: docker compose down -v"
