# Agent 2 — Infra, Container, Cloud-Local, CI/CD

> ## ⚠ ZORUNLU: integration.md PROTOKOLÜ
>
> Aşağıdaki adımlardan **herhangi birine başlamadan ÖNCE** [docs/integration.md](integration.md) dosyasını **OKUMA PROTOKOLÜ** ile oku (oku → 1 sn bekle → tekrar oku → eşitse devam).
>
> Aşağıdaki **entegrasyon noktalarına dokunduğun her seferde** [docs/integration.md](integration.md) `Work Notes` bölümüne **YAZMA PROTOKOLÜ** ile entry ekle:
> - Compose servis adları/portları (Bölüm B).
> - LocalStack init script (S3 bucket adları, Bölüm G).
> - K8s `Namespace`/`ConfigMap`/`Secret`/`Deployment`/`Service` adları (Bölüm C).
> - GitHub Actions job sırası, artifact adları (Bölüm J).
> - Postman env değişkenleri ve test sırası (Bölüm H).
> - `app/main.py`’deki export router yorum aktivasyonu (Bölüm E).
> - Yeni env değişkeni (Bölüm A — önce **🚨 Bloker** olarak yaz, orkestratör onayla).
>
> **agent1’in `GATE-1` ve `GATE-2` entry’sini integration.md’de görmeden Docker build/CI job test edemezsin** — backlog görevlerini yaz ama uçtan uca koşma.

---

> **Rol:** Uygulamanın *çalıştırılması, dağıtılması, otomasyonu*. Şartnamedeki **5 katmanı** tek başına kapatır: Docker, LocalStack (AWS), Kubernetes, GitHub Actions, Postman + Newman.
>
> **Hedef:** Sprint 1 sonunda `docker compose up` ile tam stack ayağa kalkar, `kubectl apply -f k8s/` ile Minikube’a deploy olur, GitHub Actions `ci.yml` ilk push’ta uçtan uca yeşil — **5 job: lint → pytest → docker → deploy → smoke + newman**.

---

## 1. Sahip olduğu dosyalar

```
Dockerfile                                  # multi-stage
.dockerignore
docker-compose.yml
docker-compose.override.yml                 # (opsiyonel, dev)
.env.example

app/
├── routers/
│   └── export.py                           # POST /portfolios/{id}/export (S3)
└── services/
    └── s3_service.py                       # LocalStack/AWS boto3 wrapper

scripts/
├── localstack-init.sh
├── wait-for.sh                             # postgres + localstack healthcheck
├── smoke-test.sh                           # curl /health + create portfolio
└── deploy-minikube.sh

k8s/
├── namespace.yaml
├── configmap.yaml
├── secret.yaml                             # base64 placeholder
├── deployment.yaml
├── service.yaml
├── postgres-statefulset.yaml
├── localstack-deployment.yaml
└── kustomization.yaml                      # (opsiyonel)

postman/
├── stock-portfolio.postman_collection.json # 5+ istek
├── stock-portfolio.postman_environment.json
└── README.md                               # newman komutu

.github/
└── workflows/
    └── ci.yml                              # tek workflow, 5 job

Makefile                                    # geliştirici kısayolları
```

**`app/` altındaki yegane dokunduğu yerler:**
- `app/routers/export.py` (yeni dosya)
- `app/services/s3_service.py` (yeni dosya)
- `app/main.py` içinde `# app.include_router(export.router, ...)` TODO satırını **aktive eder** (Agent 1’in bıraktığı yer).

Hiçbir koşulda Agent 1’in `models/`, `schemas/`, `services/portfolio_service.py`, `routers/portfolios.py|trades.py|health.py` dosyalarına dokunma.

---

## 2. Bağımlılıklar

| Kim’den | Ne | Ne zaman |
|---------|----|----------|
| Agent 1 | `app.main:app` çalışıyor, `/health` 200, `pyproject.toml` mevcut | Sprint 1.4 başı (Agent 1 Sprint 1.7 sonrası) |
| Agent 1 | `docs/api-contract.md` (Postman koleksiyonu için) | Sprint 1.6 başı |
| → Agent 3 | Compose’a `prometheus` ve `grafana` servisi (Agent 3 yazacak), ama port mapping ve network Agent 2 sözleşmesi | Sprint 1.2 |

**Engelleyici:** Agent 1’in `pyproject.toml`’u kesinleşmeden Dockerfile yazılır ama test edilemez. Strateji: paralel başla, Agent 1 push edince smoke test çalıştır.

---

# SPRINT 1 — MVP Infra + CI (Gün 0 – Gün 1)

> **Çıkış kriteri:** `docker compose up -d` → `/health` 200; `kubectl apply -f k8s/` Minikube’da Running; `gh workflow run ci.yml` 5 job yeşil; `newman run postman/...` 5 istek pass.

## Görev 1.1 — `.dockerignore` + temel dosyalar (15 dk)

- [ ] `.dockerignore`:
  ```
  .venv
  __pycache__
  *.pyc
  .pytest_cache
  htmlcov
  .coverage
  .git
  tests
  docs
  k8s
  .github
  postman
  *.md
  .env*
  ```
- [ ] `.env.example`:
  ```env
  DATABASE_URL=postgresql://postgres:postgres@postgres:5432/portfolio
  AWS_ENDPOINT_URL=http://localstack:4566
  AWS_ACCESS_KEY_ID=test
  AWS_SECRET_ACCESS_KEY=test
  AWS_REGION=us-east-1
  S3_BUCKET=portfolio-exports
  ENV=dev
  ```

**Kabul:** `cp .env.example .env` çalışır.

## Görev 1.2 — Multi-stage `Dockerfile` (45 dk)

**Hedef boyut:** < 200 MB.

```dockerfile
# syntax=docker/dockerfile:1.7

# ============ Stage 1: builder ============
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install --prefix=/install ".[dev]" || \
    pip install --prefix=/install "."

# ============ Stage 2: runtime ============
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/install/bin:$PATH \
    PYTHONPATH=/install/lib/python3.11/site-packages

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app app

COPY --from=builder /install /install

WORKDIR /app
COPY --chown=app:app app/ ./app/

USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **İki stage** (`builder`, `runtime`) zorunlu — rubric kalemi.
- [ ] Non-root user.
- [ ] Healthcheck.
- [ ] `docker build -t portfolio:dev .` → image < 200 MB (`docker images portfolio:dev`).

**Kabul:** `docker run --rm -p 8000:8000 portfolio:dev` çalışır, `curl localhost:8000/health` 200.

## Görev 1.3 — `docker-compose.yml` (45 dk)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: portfolio
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 10
    volumes: [pgdata:/var/lib/postgresql/data]

  localstack:
    image: localstack/localstack:3.4
    environment:
      SERVICES: s3
      DEBUG: 0
    ports: ["4566:4566"]
    volumes:
      - ./scripts/localstack-init.sh:/etc/localstack/init/ready.d/init.sh
      - localstack-data:/var/lib/localstack
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_localstack/health"]
      interval: 5s
      retries: 10

  app:
    build: .
    depends_on:
      postgres: {condition: service_healthy}
      localstack: {condition: service_healthy}
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/portfolio
      AWS_ENDPOINT_URL: http://localstack:4566
      AWS_ACCESS_KEY_ID: test
      AWS_SECRET_ACCESS_KEY: test
      AWS_REGION: us-east-1
      S3_BUCKET: portfolio-exports
    ports: ["8000:8000"]

  # Agent 3 buraya prometheus + grafana ekleyecek (Sprint 1.3 - Agent 3)

volumes:
  pgdata: {}
  localstack-data: {}
```

- [ ] `scripts/localstack-init.sh`:
  ```bash
  #!/usr/bin/env bash
  awslocal s3 mb s3://portfolio-exports
  awslocal s3 mb s3://portfolio-analysis
  echo "✓ S3 buckets ready"
  ```
  - `chmod +x` gerekli.

**Kabul:** `docker compose up -d && docker compose ps` → 3 servis healthy. `curl localhost:8000/health` 200.

## Görev 1.4 — LocalStack S3 entegrasyonu (1 saat)

`app/services/s3_service.py`:

- [ ] `class S3Service`:
  - `__init__(self, endpoint_url, bucket, access_key, secret_key, region)`
  - `client = boto3.client("s3", endpoint_url=..., aws_access_key_id=...)` (endpoint_url None ise gerçek AWS).
  - `put_object(key: str, body: bytes | str, content_type="application/json") -> str` → return s3://bucket/key.
  - `get_object(key: str) -> bytes`.
  - `list_objects(prefix: str) -> list[str]`.
- [ ] Settings’ten singleton instance (`@lru_cache` ile).

`app/routers/export.py`:

- [ ] `POST /portfolios/{id}/export`:
  - Portföydeki tüm trade’leri JSON’a serialize et.
  - `S3Service.put_object(f"portfolio-{id}/{timestamp}.json", ...)`.
  - Response: `{s3_uri: "s3://...", size_bytes: ..., trade_count: ...}`.

`app/main.py` → `from app.routers import export` import’unu **aktive et** ve `include_router` çağrısının yorumunu kaldır.

**Test (Agent 2 yazar, `tests/integration/test_export_endpoint.py`):**

- [ ] `test_export_uploads_json_to_localstack` — `moto` veya canlı LocalStack ile. CI’da LocalStack container’ı zaten var.
- [ ] `test_export_404_for_missing_portfolio`.

**Kabul:** `curl -X POST localhost:8000/portfolios/1/export` → 200 + s3_uri; `awslocal s3 ls s3://portfolio-exports/` dosyayı gösterir.

## Görev 1.5 — Kubernetes manifestleri (1 saat)

**Asgari rubric:** `Deployment`, `Service`, `ConfigMap`. Biz +`Secret`, +`StatefulSet` ekleyeceğiz.

`k8s/namespace.yaml`:
```yaml
apiVersion: v1
kind: Namespace
metadata: {name: portfolio}
```

`k8s/configmap.yaml`:
- [ ] `DATABASE_URL`, `AWS_ENDPOINT_URL`, `AWS_REGION`, `S3_BUCKET`, `ENV=prod`.

`k8s/secret.yaml`:
- [ ] `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (base64). Phase 2 için `GEMINI_API_KEY`.

`k8s/deployment.yaml`:
- [ ] 2 replica, `image: portfolio:dev` (Minikube’da load edilir).
- [ ] `envFrom`: configMapRef + secretRef.
- [ ] `livenessProbe` + `readinessProbe` → `/health`.
- [ ] `resources.requests/limits`: 100m CPU / 128Mi mem, limit 500m / 512Mi.
- [ ] `imagePullPolicy: IfNotPresent`.

`k8s/service.yaml`:
- [ ] `type: NodePort`, port 8000 → nodePort 30080.

`k8s/postgres-statefulset.yaml`:
- [ ] postgres:16-alpine + PVC.

`k8s/localstack-deployment.yaml`:
- [ ] LocalStack S3, ClusterIP service.

`scripts/deploy-minikube.sh`:
```bash
#!/usr/bin/env bash
set -e
minikube start --driver=docker
eval $(minikube docker-env)
docker build -t portfolio:dev .
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ -n portfolio
kubectl rollout status deployment/portfolio-app -n portfolio --timeout=120s
echo "Service: $(minikube service portfolio-app -n portfolio --url)"
```

**Kabul:** `bash scripts/deploy-minikube.sh` → `kubectl get pods -n portfolio` tümü `Running`. `curl $(minikube service portfolio-app -n portfolio --url)/health` 200.

## Görev 1.6 — Postman koleksiyonu + Newman (45 dk)

`postman/stock-portfolio.postman_collection.json` — **en az 5 istek**, her birinde test scripti:

| # | İsim | Method | URL | Test |
|---|------|--------|-----|------|
| 1 | Health Check | GET | `{{baseUrl}}/health` | `pm.expect(pm.response.code).to.eql(200)` |
| 2 | Create Portfolio | POST | `{{baseUrl}}/portfolios` | status 201, save `portfolio_id` to env |
| 3 | Add BUY Trade | POST | `{{baseUrl}}/portfolios/{{portfolio_id}}/trades` | status 201, save `trade_id` |
| 4 | List Trades | GET | `{{baseUrl}}/portfolios/{{portfolio_id}}/trades` | status 200, array length ≥ 1 |
| 5 | Get Summary | GET | `{{baseUrl}}/portfolios/{{portfolio_id}}/summary` | status 200, `total_pnl` exists |
| 6 | Add SELL Trade | POST | `{{baseUrl}}/portfolios/{{portfolio_id}}/trades` | status 201, `realized_pnl` arttı |
| 7 | Export to S3 | POST | `{{baseUrl}}/portfolios/{{portfolio_id}}/export` | status 200, `s3_uri` startsWith `s3://` |

`postman/stock-portfolio.postman_environment.json`:
- [ ] `baseUrl` = `http://localhost:8000` (lokal), `http://app:8000` (CI compose içinde).

**Kabul:**
```bash
npx newman run postman/stock-portfolio.postman_collection.json \
  -e postman/stock-portfolio.postman_environment.json \
  --reporters cli,htmlextra --reporter-htmlextra-export newman-report.html
```
→ 7 request, 0 fail.

## Görev 1.7 — GitHub Actions `ci.yml` (1.5 saat) — **rubric’in en görünür kalemi**

`.github/workflows/ci.yml` tek dosya, **5 job**:

```yaml
name: CI
on:
  push: {branches: [main, develop]}
  pull_request: {branches: [main]}

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11', cache: pip}
      - run: pip install ruff
      - run: ruff check app tests
      - run: ruff format --check app tests

  test:
    needs: lint
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: {POSTGRES_PASSWORD: postgres, POSTGRES_DB: portfolio}
        ports: ['5432:5432']
        options: --health-cmd "pg_isready -U postgres" --health-interval 5s --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11', cache: pip}
      - run: pip install -e ".[dev]"
      - name: Pytest with coverage
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/portfolio
        run: pytest --cov=app --cov-report=xml --cov-report=term --cov-fail-under=70
      - uses: actions/upload-artifact@v4
        with: {name: coverage, path: coverage.xml}

  docker:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: Build image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: false
          load: true
          tags: portfolio:ci
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Save image
        run: docker save portfolio:ci | gzip > portfolio.tar.gz
      - uses: actions/upload-artifact@v4
        with: {name: image, path: portfolio.tar.gz}

  deploy-smoke:
    needs: docker
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: {name: image}
      - run: docker load -i portfolio.tar.gz
      - name: Compose up
        run: |
          docker tag portfolio:ci portfolio:dev
          docker compose up -d
          ./scripts/wait-for.sh http://localhost:8000/health 60
      - name: Smoke test
        run: ./scripts/smoke-test.sh

  newman:
    needs: deploy-smoke
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: {name: image}
      - run: docker load -i portfolio.tar.gz && docker tag portfolio:ci portfolio:dev
      - run: docker compose up -d && ./scripts/wait-for.sh http://localhost:8000/health 60
      - uses: actions/setup-node@v4
        with: {node-version: '20'}
      - run: npm install -g newman newman-reporter-htmlextra
      - run: |
          newman run postman/stock-portfolio.postman_collection.json \
            -e postman/stock-portfolio.postman_environment.json \
            --reporters cli,htmlextra \
            --reporter-htmlextra-export newman-report.html
      - uses: actions/upload-artifact@v4
        if: always()
        with: {name: newman-report, path: newman-report.html}
```

- [ ] `scripts/wait-for.sh`: bir URL’i N saniye boyunca 200 dönene kadar pingle.
- [ ] `scripts/smoke-test.sh`:
  ```bash
  set -e
  curl -fsS localhost:8000/health
  ID=$(curl -fsS -X POST localhost:8000/portfolios -H 'Content-Type: application/json' \
    -d '{"name":"smoke","currency":"USD"}' | jq -r '.id')
  curl -fsS -X POST localhost:8000/portfolios/$ID/trades \
    -H 'Content-Type: application/json' \
    -d '{"ticker":"AAPL","trade_type":"BUY","quantity":10,"price":150}'
  curl -fsS localhost:8000/portfolios/$ID/summary | jq .
  echo "✓ smoke ok"
  ```

**Kabul:** GitHub’a push → Actions sekmesinde 5 job sıralı yeşil. Newman raporu artifact olarak indirilebilir.

## Görev 1.8 — `Makefile` (15 dk)

```makefile
.PHONY: install run test cov build up down smoke newman k8s clean

install:    ; pip install -e ".[dev]"
run:        ; uvicorn app.main:app --reload
test:       ; pytest -v
cov:        ; pytest --cov=app --cov-report=term-missing --cov-fail-under=70
build:      ; docker build -t portfolio:dev .
up:         ; docker compose up -d
down:       ; docker compose down -v
smoke:      ; ./scripts/smoke-test.sh
newman:     ; newman run postman/stock-portfolio.postman_collection.json -e postman/stock-portfolio.postman_environment.json
k8s:        ; ./scripts/deploy-minikube.sh
clean:      ; rm -rf .pytest_cache htmlcov .coverage *.tar.gz
```

## Görev 1.9 — integration.md sync (zorunlu, 10 dk)

- [ ] OKUMA PROTOKOLÜ.
- [ ] YAZMA PROTOKOLÜ ile entry:
  - **Başlık:** `agent2 sprint-1 docker+k8s+ci+newman`
  - **Etkilenen noktalar:** B (5 compose servisi), C (tüm k8s adları), G (S3 bucket’lar yaratıldı), H (Postman env değişkenleri), J (artifact’lar üretiliyor), D.8 endpoint canlı, E `app/main.py` export router yorum aktive.
  - **agent3 için not:** Compose’da `prometheus`/`grafana` portları rezervli (9090/3000); ekleyebilirsin. `ci.yml` `test` job’unda Playwright adımı için **placeholder yok**, kendi Sprint 1’inde sen ekle.
  - **agent1 için not:** GATE-2 ön koşulu sağlanmış olmalı; sağlanmadıysa **bloker** olarak yaz.
  - **Doğrulama komutu:** `docker compose up -d && curl localhost:8000/health && newman run postman/...`
  - **Bağlı GATE:** `agent2 GATE-1`, `agent2 GATE-2`, `agent2 GATE-3` → `[x]`.

**Sprint 1 DoD:**
- ✅ `docker build .` < 200 MB, multi-stage 2 stage
- ✅ `docker compose up -d` 3 servis healthy
- ✅ `awslocal s3 ls` bucket gösterir; `/portfolios/{id}/export` çalışır
- ✅ Minikube’da `kubectl get pods -n portfolio` tüm pod Running
- ✅ Postman 7 istek + Newman lokal yeşil
- ✅ GitHub Actions `ci.yml` 5 job yeşil
- ✅ `docs/integration.md` Work Note eklendi, GATE-1/2/3 bildirildi
- ✅ Commit: `feat(infra): sprint-1 docker+k8s+ci+newman pipeline`

---

# SPRINT 2 — Sağlamlaştırma (Gün 2)

## Görev 2.1 — Image boyutu optimizasyonu

- [ ] `python:3.11-slim` yerine `python:3.11-slim-bookworm`.
- [ ] Wheel cache + `--no-deps` ile pin’li install (`pip-tools` ile `requirements.txt` generate).
- [ ] `docker images` → < 150 MB hedefi.
- [ ] Trivy scan: `docker run aquasec/trivy image portfolio:dev` → critical 0.

## Görev 2.2 — CI cache + paralelleştirme

- [ ] `actions/setup-python` cache pip; `actions/cache` `~/.cache/pip` ve `.venv`.
- [ ] `test` ve `docker` job’ları paralel (lint sonrası `needs: lint` her ikisinde).
- [ ] Branch protection: `main`’e merge için tüm job yeşil + 1 review (kendi PR’ında approve).

## Görev 2.3 — K8s sağlamlaştırma

- [ ] `HorizontalPodAutoscaler` (CPU %70).
- [ ] `NetworkPolicy`: app sadece postgres + localstack’a çıkabilir.
- [ ] `PodDisruptionBudget`: minAvailable 1.
- [ ] `kustomization.yaml` ile base/overlay ayrımı (`overlays/dev`, `overlays/ci`).

## Görev 2.4 — Postman koleksiyonunu zenginleştir

- [ ] Negative testler: invalid trade → 400, missing portfolio → 404.
- [ ] Pre-request script: auth header (gelecekte JWT eklenirse).
- [ ] `data.json` ile Newman iteration (3 farklı portföy).

## Görev 2.5 — integration.md sync

- [ ] OKUMA → YAZMA. Entry: `agent2 sprint-2 hardening`. HPA / NetworkPolicy değişikliklerini Bölüm C’ye **bloker olarak öner**.

**Sprint 2 DoD:**
- ✅ Image < 150 MB, Trivy critical 0
- ✅ CI runtime < 4 dk (cache sayesinde)
- ✅ K8s HPA + NetworkPolicy aktif
- ✅ Postman 10+ istek, negative dahil
- ✅ `integration.md` Work Note eklendi

---

# SPRINT 3 — Phase 2 + Bonus (Gün 3)

## Görev 3.1 — Gemini scheduled workflow

`.github/workflows/daily-analysis.yml`:
- [ ] `on: schedule: cron: "0 18 * * 1-5"` (hafta içi 18:00 UTC).
- [ ] Job: deploy edilmiş app’a `POST /portfolios/{id}/analysis/daily` istek atar.
- [ ] Sonucu artifact + commit `docs/analysis/YYYY-MM-DD.md`.

## Görev 3.2 — Helm chart (Bonus +5)

```
helm/
└── portfolio/
    ├── Chart.yaml
    ├── values.yaml
    └── templates/{deployment,service,configmap,secret,hpa}.yaml
```
- [ ] `helm install portfolio ./helm/portfolio -n portfolio` çalışır.

## Görev 3.3 — KEDA event-driven (Bonus +5)

- [ ] `ScaledObject`: `/metrics` üzerinden `http_requests_per_second > 100` ise replica 5’e çıkar.

## Görev 3.4 — integration.md sync

- [ ] OKUMA → YAZMA. Entry: `agent2 sprint-3 phase2 helm+cron+keda`.
  - K8s secret’a `GEMINI_API_KEY` eklendi (Bölüm C). agent1’in Phase 2 servisi bunu okur.

**Sprint 3 DoD:**
- ✅ Cron workflow yeşil koşu
- ✅ Helm chart deploy
- ✅ (Opsiyonel) KEDA scale demo
- ✅ Bonus puan +5 ile +15 arası
- ✅ `integration.md` Work Note eklendi

---

## Komut özet kartı (Agent 2)

```bash
# Docker
docker build -t portfolio:dev .
docker images portfolio:dev                    # boyut kontrol
docker run --rm -p 8000:8000 portfolio:dev

# Compose
docker compose up -d
docker compose logs -f app
docker compose down -v

# LocalStack
awslocal s3 ls
awslocal s3 ls s3://portfolio-exports/

# Kubernetes
minikube start --driver=docker
eval $(minikube docker-env)
bash scripts/deploy-minikube.sh
kubectl get all -n portfolio
kubectl logs -f deploy/portfolio-app -n portfolio
minikube service portfolio-app -n portfolio --url

# Postman / Newman
newman run postman/stock-portfolio.postman_collection.json \
  -e postman/stock-portfolio.postman_environment.json \
  --reporters cli,htmlextra --reporter-htmlextra-export newman-report.html

# CI lokal simülasyon
act -j lint                                    # act kuruluysa
gh workflow run ci.yml
gh run watch
```

---

## Risk / dikkat noktaları

1. **PowerShell vs bash:** Smoke test ve init script’leri bash. Windows’ta `git-bash` veya WSL kullan. CI Linux olduğu için sorun yok.
2. **LocalStack init hook:** `/etc/localstack/init/ready.d/` v3.x’te çalışır; v2.x’te `awslocal s3 mb` farklı path. Image versiyonunu pin’le.
3. **Minikube image:** Lokal image’ı Minikube’a yüklemek için `eval $(minikube docker-env)` zorunlu, yoksa `ErrImagePull` alırsın.
4. **GitHub Actions service container:** Postgres `services:` bloğunda; Testcontainers GH runner’da Docker-in-Docker gerektirir — `test` job’unda runner zaten Docker’a sahip, sorun yok ama `--privileged` gerekmez.
5. **`app/main.py` çakışması:** Agent 1’in bıraktığı yorum satırını aç; commit message açık olsun (`feat(export): wire S3 export router`).
6. **Postman environment:** CI’da `baseUrl=http://localhost:8000` çünkü compose host’a port maplemiş. Container içinde Newman koşarsa `http://app:8000`.
