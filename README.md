# Stock Portfolio Tracker

FastAPI tabanlı portföy ve işlem takibi: P&amp;L özeti, S3 export, Prometheus metrikleri, Playwright E2E ve k6 performans testleri. Statik web arayüzü `/ui` altında servis edilir.

![Architecture](docs/architecture.png)

> PNG: `npx @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/architecture.png`

## Quick start

```bash
docker compose up -d
# UI (agent1 /ui mount aktif olduktan sonra)
open http://localhost:8000/ui/
open http://localhost:3000          # Grafana (admin/admin)
open http://localhost:9090          # Prometheus
```

## Test commands

```bash
pytest --cov=app --cov-fail-under=70
pytest tests/e2e -v
newman run postman/stock-portfolio.postman_collection.json -e postman/stock-portfolio.postman_environment.json
playwright install chromium && pytest tests/e2e
bash scripts/run-perf.sh
```

## API endpoints (summary)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/portfolios` | Create portfolio |
| GET | `/portfolios/{id}` | Portfolio + positions |
| POST | `/portfolios/{id}/trades` | Add trade |
| GET | `/portfolios/{id}/trades` | List trades |
| GET | `/portfolios/{id}/summary` | P&amp;L summary |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

Details: [docs/api-contract.md](docs/api-contract.md)

## Rubric checklist (14 items)

| # | Item | Status |
|---|------|--------|
| 1 | FastAPI mini service | Agent 1 |
| 2 | Pytest + coverage ≥ 70% | Agent 1 |
| 3 | PostgreSQL + Testcontainers | Agent 1 |
| 4 | Factory Boy test data | Agent 1 |
| 5 | Multi-stage Docker | Agent 2 |
| 6 | LocalStack S3 | Agent 2 |
| 7 | Kubernetes manifests | Agent 2 |
| 8 | GitHub Actions 5 jobs | Agent 2 + 3 |
| 9 | Postman + Newman | Agent 2 |
| 10 | Static Web UI (3 pages) | Agent 3 |
| 11 | Playwright E2E (5 scenarios) | Agent 3 |
| 12 | Prometheus + Grafana (3 panels) | Agent 3 |
| 13 | k6 performance (p95 &lt; 500ms) | Agent 3 |
| 14 | README + architecture + final report | Agent 3 |

## Documentation

- [Architecture](docs/architecture.md)
- [Final report](docs/final-report.md)
- [Demo script](docs/demo-script.md)
- [Integration protocol](docs/integration.md)

## License

MIT — see [LICENSE](LICENSE).

## AI usage

Portions of UI, monitoring dashboards, E2E tests, and documentation were drafted with AI assistance and reviewed against `docs/integration.md` and `docs/api-contract.md`.
