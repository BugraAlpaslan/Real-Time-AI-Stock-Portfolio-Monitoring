#!/usr/bin/env bash
set -euo pipefail
curl -fsS localhost:8000/health
ID=$(curl -fsS -X POST localhost:8000/portfolios -H "Content-Type: application/json" \
  -d '{"name":"smoke","currency":"USD"}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -fsS -X POST "localhost:8000/portfolios/${ID}/trades" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","trade_type":"BUY","quantity":10,"price":150}'
curl -fsS "localhost:8000/portfolios/${ID}/summary"
echo "smoke ok"
