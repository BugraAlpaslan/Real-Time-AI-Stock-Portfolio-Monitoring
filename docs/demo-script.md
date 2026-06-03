# Demo script (~10 minutes)

## 1. Introduction (1 min)

- Stock Portfolio Tracker: FastAPI backend, static UI, full quality stack.
- Four layers today: monitoring, performance, E2E, documentation.

## 2. Architecture (2 min)

- Show `docs/architecture.md` diagram: UI → API → Postgres, metrics → Prometheus → Grafana.
- Mention Agent 1 (API/P&amp;L), Agent 2 (Docker/CI/S3), Agent 3 (UI/observability/perf).

## 3. Live UI (2 min)

```bash
docker compose up -d
# open http://localhost:8000/ui/
```

- Create portfolio, BUY trade, open summary page.
- Show error: SELL without position → `INSUFFICIENT_POSITION` banner.

## 4. Tests (2 min)

```bash
pytest --cov=app
pytest tests/e2e -v
newman run postman/stock-portfolio.postman_collection.json -e postman/...
bash scripts/run-perf.sh
```

## 5. Observability (2 min)

- Prometheus: http://localhost:9090/targets → `portfolio-app` UP.
- Grafana: http://localhost:3000 → **Portfolio Overview** (3 panels).
- Run k6 briefly to populate graphs.

## 6. CI (1 min)

- GitHub Actions: 5 jobs, artifacts (coverage, image, newman-report).

## Q&amp;A cheat sheet

| Question | Answer |
|----------|--------|
| Realized P&amp;L formula? | `(sell_price - avg_cost) * qty - commission` per sell |
| What is p95? | 95th percentile latency; 95% of requests faster than this value |
| Why Testcontainers? | Real PostgreSQL in CI without mocking SQL dialect differences |
| Why LocalStack? | Same S3 API as AWS, no cloud bill for demos |
