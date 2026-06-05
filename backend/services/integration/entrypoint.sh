#!/usr/bin/env bash
# Launch uvicorn + the SQS backfill consumer side-by-side.
#
# Both processes must run inside the same container for V1 (single ECS
# service definition). When either exits non-zero, the script exits — ECS
# replaces the task.
set -eu

PORT="${PORT:-8002}"

# Start uvicorn in the background.
uvicorn integration.main:app --host 0.0.0.0 --port "${PORT}" --no-access-log &
UVICORN_PID=$!

# Start the SQS consumer in the background.
python -m integration.app.consumer_main &
CONSUMER_PID=$!

# Forward SIGTERM to children so ECS draining is clean.
trap 'kill -TERM "${UVICORN_PID}" "${CONSUMER_PID}" 2>/dev/null || true' TERM INT

# Exit when either child exits.
wait -n "${UVICORN_PID}" "${CONSUMER_PID}"
EXIT_CODE=$?
kill -TERM "${UVICORN_PID}" "${CONSUMER_PID}" 2>/dev/null || true
exit "${EXIT_CODE}"
