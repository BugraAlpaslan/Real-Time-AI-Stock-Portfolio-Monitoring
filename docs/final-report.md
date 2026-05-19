# Final Report — Stock Portfolio Tracker

## 1. Project summary

Stock Portfolio Tracker is a teaching and rubric-oriented portfolio management API with a static web UI, automated tests, observability, and performance gates. Users create portfolios, record BUY/SELL trades, and view realized/unrealized P&amp;L on a summary dashboard. The system targets local-first development via Docker Compose (PostgreSQL, LocalStack, Prometheus, Grafana) and a five-job GitHub Actions pipeline.

## 2. Architecture decisions

**FastAPI** provides OpenAPI documentation, dependency injection for database sessions, and native async support for future external price feeds (Midas API in Phase 2).

**PostgreSQL** is the production-like store in Compose and CI; SQLite memory accelerates unit tests. **Testcontainers** (Agent 1) validates SQL compatibility without a manually provisioned database.

**LocalStack** emulates S3 for export and analysis buckets with the same boto3 code path as AWS.

**Vanilla static UI** avoids build tooling while satisfying Playwright E2E requirements; portfolio list uses browser `localStorage` because the API exposes per-id GET only (no list endpoint).

**Prometheus + Grafana** use default `prometheus-fastapi-instrumentator` metric names so dashboard queries remain portable across environments.

## 3. Test strategy

| Layer | Tool | Scope |
|-------|------|--------|
| Unit | pytest | P&amp;L math, schemas, factories |
| Integration | pytest + TestClient | HTTP + DB |
| Testcontainers | pytest | PostgreSQL-specific flows |
| E2E | Playwright | 5 UI scenarios via `data-testid` |
| Contract | Newman | Postman collection (Agent 2) |
| Performance | k6 | Trade + summary, p95 threshold |

Coverage target: **≥ 70%** on `app/` (`pyproject.toml` `fail_under = 70`). E2E tests **skip** when `/health` is unreachable (agent1 GATE-2 pending) rather than failing the suite.

## 4. CI/CD and deployment

Workflow jobs (`.github/workflows/ci.yml`):

1. **lint** — ruff check/format
2. **test** — pytest coverage + Playwright (when `app/main.py` exists)
3. **docker** — multi-stage image build
4. **deploy-smoke** — `docker compose up`, health wait, smoke script
5. **newman** — API collection regression

Kubernetes manifests (Agent 2) target namespace `portfolio` with ConfigMap/Secret-driven configuration. Minikube deploy script validates cluster paths.

## 5. Observability and performance

**Metrics:** `http_requests_total`, `http_request_duration_seconds_bucket` scraped from `/metrics` every 10s.

**Grafana dashboard** (*Portfolio Overview*):

| Panel | Query purpose |
|-------|----------------|
| Request rate | Traffic by method/status |
| Latency p50/p95/p99 | SLO tracking |
| Error rate % | 5xx share of requests |

**k6** (`scripts/k6/load.js`): ramp 20→50 VUs, threshold `p(95)<500ms` on summary group, output `docs/perf-report.json`.

*Pending live verification until `docker compose up` and agent1 GATE-2.*

## 6. Challenges and learnings

- **Decimal precision:** Financial quantities use decimal strings in JSON to avoid float drift; UI parses for display only.
- **Cross-agent sequencing:** UI mount in `app/main.py` must activate only after `static/` exists; E2E depends on backend health gate.
- **AI usage:** Scaffolding (dashboard JSON, E2E selectors, docs) was AI-assisted; all metric names and API error codes were validated against `integration.md` and `api-contract.md`.

## Appendix: Command reference

```bash
docker compose up -d
uvicorn app.main:app --reload
pytest --cov=app
pytest tests/e2e -v
bash scripts/run-perf.sh
newman run postman/stock-portfolio.postman_collection.json -e postman/stock-portfolio.postman_environment.json
```

Repository: `testmuh` (local workspace).
