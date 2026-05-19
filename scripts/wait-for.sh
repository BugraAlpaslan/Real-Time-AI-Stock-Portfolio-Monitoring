#!/usr/bin/env bash
set -euo pipefail
URL="${1:?url required}"
TIMEOUT="${2:-60}"
for ((i = 0; i < TIMEOUT; i++)); do
  if curl -fsS "$URL" >/dev/null 2>&1; then
    echo "ready: $URL"
    exit 0
  fi
  sleep 1
done
echo "timeout waiting for $URL" >&2
exit 1
