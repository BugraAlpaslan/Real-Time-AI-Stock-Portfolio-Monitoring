#!/usr/bin/env bash
set -euo pipefail
BUCKET="${1:-portfolio-exports}"
TIMEOUT="${2:-60}"
for ((i = 0; i < TIMEOUT; i++)); do
  if docker compose exec -T localstack awslocal s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
    echo "ready: s3://${BUCKET}"
    exit 0
  fi
  sleep 1
done
echo "timeout waiting for s3://${BUCKET}" >&2
exit 1
