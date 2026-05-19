#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

docker run --rm --network host \
  -v "${ROOT}/scripts/k6:/scripts" \
  -v "${ROOT}/docs:/docs" \
  -e "BASE_URL=${BASE_URL}" \
  grafana/k6:0.50.0 run /scripts/load.js
