# k6 performance tests

## Prerequisites

- Application reachable at `BASE_URL` (default `http://localhost:8000`)
- Docker (recommended) or local k6 install

## Run

```bash
# Linux / macOS / Git Bash
bash scripts/run-perf.sh

# Windows PowerShell
$env:BASE_URL="http://localhost:8000"
docker run --rm --network host -v "${PWD}/scripts/k6:/scripts" -v "${PWD}/docs:/docs" -e BASE_URL=$env:BASE_URL grafana/k6:0.50.0 run /scripts/load.js
```

Output: `docs/perf-report.json` and threshold summary on stdout.
