# Agent 3 — UI, E2E, Observability, Performans, Belgeler

> ## ⚠ ZORUNLU: integration.md PROTOKOLÜ
>
> Aşağıdaki adımlardan **herhangi birine başlamadan ÖNCE** [docs/integration.md](integration.md) dosyasını **OKUMA PROTOKOLÜ** ile oku (oku → 1 sn bekle → tekrar oku → eşitse devam).
>
> Aşağıdaki **entegrasyon noktalarına dokunduğun her seferde** [docs/integration.md](integration.md) `Work Notes` bölümüne **YAZMA PROTOKOLÜ** ile entry ekle:
> - `app/main.py` `/ui` mount aktivasyonu (Bölüm E).
> - `docker-compose.yml`’a `prometheus`/`grafana` servisleri eklenmesi (Bölüm B).
> - `pyproject.toml`’a `pytest-playwright` ekleme (Bölüm E).
> - `.github/workflows/ci.yml` `test` job’una Playwright adımı eklenmesi (Bölüm E).
> - Prometheus scrape config + metric query’leri (Bölüm F).
> - k6 `BASE_URL` env (Bölüm A).
> - `E2E_BASE_URL` env (Bölüm A).
>
> **agent1 `GATE-2` (uvicorn çalışıyor) ve agent2 `GATE-1` (compose ayakta) bildirilmeden** E2E ve Grafana entegrasyonu canlıda doğrulanamaz — kodu yaz ama dependency hazır olana kadar `xfail`/skip kullan ve sprint sonu sync entry’sinde bekleme durumunu raporla.

---

> **Rol:** Kullanıcıya görünen yüz, gözlemlenebilirlik, performans ve dokümantasyon. Şartnamedeki **4 katmanı** tek başına kapatır: Monitoring (Prometheus + Grafana), Performans (k6/Locust), E2E (Playwright), Belgeler. Ek olarak basit bir **Web UI** kurar — Playwright bu UI üstünde çalışır.
>
> **Hedef:** Sprint 1 sonunda Playwright 5 senaryo yeşil, k6 raporu `p(95) < 500ms`, Grafana’da 3 panel canlı veri, README + mimari diyagram + final rapor commit.

---

## 1. Sahip olduğu dosyalar

```
static/
├── index.html              # portföy listesi + oluşturma formu
├── portfolio.html          # portföy detayı + trade formu + pozisyonlar
├── summary.html            # P&L özet kartları
├── css/styles.css
└── js/
    ├── api.js              # fetch wrapper
    ├── portfolios.js
    ├── trades.js
    └── summary.js

tests/e2e/
├── __init__.py
├── conftest.py             # Playwright fixture, base_url
├── playwright.config.py    # (pytest-playwright kullanıyorsak gerekmez)
├── test_create_portfolio.py
├── test_buy_trade.py
├── test_sell_trade_pnl.py
├── test_summary_view.py
└── test_invalid_trade.py

monitoring/
├── prometheus.yml
├── docker-compose.monitoring.yml          # (veya ana compose'a merge)
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/prometheus.yml
│   │   └── dashboards/dashboard.yml
│   └── dashboards/
│       └── portfolio-overview.json        # 3 panel
└── alerts.yml                              # (opsiyonel sprint 2)

scripts/
├── k6/
│   ├── load.js                             # ramp-up + thresholds
│   ├── soak.js                             # (sprint 2)
│   └── README.md
├── locustfile.py                           # k6 yerine kullanılırsa
└── run-perf.sh

docs/
├── architecture.md                         # mimari diyagram + açıklama
├── architecture.png                        # (verdiğiniz görsel + güncelleme)
├── architecture.mmd                        # mermaid kaynak
├── final-report.md                         # 4-6 sayfa
├── api-contract.md                         # (Agent 1 yazdı, Agent 3 review)
├── screenshots/                            # UI + Grafana + Newman
└── demo-script.md                          # sunum sırası

README.md                                   # repo kapağı
LICENSE                                     # MIT
```

**`app/` altında dokunduğu yer:** YOK. Yalnızca Agent 1’in `main.py`’deki `# app.mount("/ui", ...)` placeholder yorumunu **aktive eder** (UI dosyaları hazır olduktan sonra).

---

## 2. Bağımlılıklar

| Kim’den | Ne | Ne zaman |
|---------|----|----------|
| Agent 1 | `/health`, `/portfolios`, `/trades`, `/summary`, `/metrics` çalışıyor | Sprint 1.3 başı |
| Agent 1 | `docs/api-contract.md` | Sprint 1 başı |
| Agent 2 | `docker compose up` ile app erişilebilir | Sprint 1.4 (E2E + perf için) |

**Engelleyici çözümü:** Agent 1 daha bitmediyse Playwright testleri **stub API** (msw veya `respx`-benzeri) ile başlatılmaz; bunun yerine ilk E2E **dry-run mode**’da yazılır, Agent 1 hazır olunca gerçek backend’e bağlanır.

---

# SPRINT 1 — MVP Tüm Katmanlar (Gün 0 – Gün 1)

> **Çıkış kriteri:** UI 3 sayfa açılıyor; Playwright 5 senaryo yeşil; Prometheus 3 panel veri gösteriyor; k6 raporu `p(95) < 500ms` `OK`; README + mimari + final rapor commit edilmiş.

## Görev 1.1 — Basit Web UI (2 saat)

**Stil tercihi:** Tek HTML + Vanilla JS + fetch. Çerçeve **yok** (basit tutmak rubric’i karşılar, Playwright için fazlasıyla yeterli).

`static/index.html` (portföy listesi + oluşturma):

- [ ] `<form id="create-portfolio-form">` → name, currency.
- [ ] `<ul id="portfolio-list">` → JS ile API’den çek, her item `<a href="portfolio.html?id={id}">`.
- [ ] `<div data-testid="success-toast" hidden>` — Playwright bunu bekleyecek.

`static/portfolio.html` (detay + trade formu):

- [ ] URL’den `?id=` oku.
- [ ] Portföy başlık + pozisyon tablosu.
- [ ] Trade formu: ticker, BUY/SELL, quantity, price, commission.
- [ ] Submit sonrası tablo yenilenir.
- [ ] Hata mesajı için `<div data-testid="error-banner">`.

`static/summary.html`:

- [ ] 3 kart: `data-testid="realized-pnl"`, `unrealized-pnl`, `total-pnl`.
- [ ] Pozisyon tablosu (ticker, qty, avg, market, pnl).

`static/js/api.js`:
```js
const API = window.location.origin;
export async function api(method, path, body) {
  const r = await fetch(`${API}${path}`, {
    method,
    headers: {'Content-Type': 'application/json'},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  return r.json();
}
```

- [ ] Agent 1’den `app/main.py`’deki `app.mount("/ui", StaticFiles(directory="static", html=True))` satırını **aktive et**.

**Kabul:** `uvicorn app.main:app` + tarayıcıda `http://localhost:8000/ui/` → 3 sayfa gezilir, portföy + trade ekleme manuel olarak çalışır.

## Görev 1.2 — Playwright kurulumu + E2E senaryolar (2 saat)

- [ ] `pip install pytest-playwright` (Agent 1’in `pyproject.toml`’una `[project.optional-dependencies] e2e = ["pytest-playwright>=0.4"]` ekle).
- [ ] `playwright install chromium`.

`tests/e2e/conftest.py`:
```python
import pytest

@pytest.fixture(scope="session")
def base_url():
    import os
    return os.getenv("E2E_BASE_URL", "http://localhost:8000")

@pytest.fixture
def ui(page, base_url):
    page.goto(f"{base_url}/ui/")
    return page
```

**5 senaryo zorunlu (rubric: 3-5):**

`tests/e2e/test_create_portfolio.py`:
- [ ] `test_user_creates_portfolio_and_sees_it_in_list`
  - Forma "E2E Test" yaz, currency=USD, submit.
  - Listede "E2E Test" görünür.
  - `data-testid="success-toast"` görünür hale geliyor.

`tests/e2e/test_buy_trade.py`:
- [ ] `test_user_adds_buy_trade_and_position_appears`
  - Portföy oluştur → linki tıkla.
  - BUY AAPL 10@150 ekle.
  - Pozisyon tablosunda AAPL satırı, qty=10, avg=150.

`tests/e2e/test_sell_trade_pnl.py`:
- [ ] `test_sell_after_buy_creates_realized_pnl`
  - Önce 10@100 BUY, sonra 5@130 SELL.
  - Summary sayfasında `realized-pnl` = ~150 (komisyonsuz varsayım).

`tests/e2e/test_summary_view.py`:
- [ ] `test_summary_displays_all_pnl_cards`
  - 3 kart görünür, total = realized + unrealized.
  - Pozisyon tablosu satır sayısı doğru.

`tests/e2e/test_invalid_trade.py`:
- [ ] `test_sell_without_position_shows_error_banner`
  - SELL TSLA 5@200 → hiç pozisyon yok.
  - `data-testid="error-banner"` görünür, içeriği `INSUFFICIENT_POSITION` içerir.

**Kabul:**
```bash
pytest tests/e2e --headed     # görsel debug
pytest tests/e2e              # CI modu
```
→ 5 test yeşil.

CI’a entegrasyon: Agent 2’nin `ci.yml` test job’una yeni step:
```yaml
- run: playwright install --with-deps chromium
- run: pytest tests/e2e
  env:
    E2E_BASE_URL: http://localhost:8000
```

## Görev 1.3 — Prometheus + Grafana stack (1.5 saat)

`monitoring/prometheus.yml`:
```yaml
global:
  scrape_interval: 10s
  evaluation_interval: 10s
scrape_configs:
  - job_name: portfolio-app
    static_configs:
      - targets: ['app:8000']
    metrics_path: /metrics
```

`monitoring/grafana/provisioning/datasources/prometheus.yml`:
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

`monitoring/grafana/provisioning/dashboards/dashboard.yml`:
```yaml
apiVersion: 1
providers:
  - name: portfolio
    folder: ''
    type: file
    options: {path: /etc/grafana/dashboards}
```

**Ana compose’a (Agent 2 ile koordineli) eklenecek servisler:**
```yaml
prometheus:
  image: prom/prometheus:v2.52.0
  volumes: ['./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml']
  ports: ['9090:9090']

grafana:
  image: grafana/grafana:10.4.2
  depends_on: [prometheus]
  environment:
    GF_SECURITY_ADMIN_USER: admin
    GF_SECURITY_ADMIN_PASSWORD: admin
    GF_AUTH_ANONYMOUS_ENABLED: 'true'
  volumes:
    - './monitoring/grafana/provisioning:/etc/grafana/provisioning'
    - './monitoring/grafana/dashboards:/etc/grafana/dashboards'
  ports: ['3000:3000']
```

`monitoring/grafana/dashboards/portfolio-overview.json` — **3 panel zorunlu**:

| Panel | Tip | Query | Birim |
|-------|-----|-------|-------|
| 1. Request rate | Time series | `sum(rate(http_requests_total[1m])) by (method, status)` | req/s |
| 2. Latency p50/p95/p99 | Time series | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))` | seconds |
| 3. Error rate (%) | Stat (gauge) | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100` | percent |

Bonus panel’ler (opsiyonel sprint 2): aktif portfolio sayısı (custom counter), DB latency.

- [ ] Dashboard JSON’u Grafana UI’dan export ederek elde et (provisioning ile auto-load).

**Kabul:**
- `docker compose up -d`
- `http://localhost:9090/targets` → portfolio-app UP
- `http://localhost:3000` → admin/admin → "Portfolio Overview" dashboard 3 panel, veri akıyor (k6 koşturduktan sonra grafikler dolacak).

## Görev 1.4 — k6 performans testi (1 saat)

`scripts/k6/load.js`:
```js
import http from 'k6/http';
import { check, sleep, group } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m',  target: 50 },
    { duration: '30s', target: 0  },
  ],
  thresholds: {
    'http_req_duration{group:::summary}': ['p(95)<500'],
    'http_req_failed': ['rate<0.01'],
    'checks': ['rate>0.99'],
  },
};

const BASE = __ENV.BASE_URL || 'http://localhost:8000';

export function setup() {
  const r = http.post(`${BASE}/portfolios`,
    JSON.stringify({ name: `perf-${Date.now()}`, currency: 'USD' }),
    { headers: { 'Content-Type': 'application/json' } });
  return { portfolioId: r.json('id') };
}

export default function (data) {
  group('create_trade', () => {
    const r = http.post(`${BASE}/portfolios/${data.portfolioId}/trades`,
      JSON.stringify({ ticker: 'AAPL', trade_type: 'BUY', quantity: 1, price: 150 }),
      { headers: { 'Content-Type': 'application/json' } });
    check(r, { 'trade 201': r => r.status === 201 });
  });

  group('summary', () => {
    const r = http.get(`${BASE}/portfolios/${data.portfolioId}/summary`);
    check(r, { 'summary 200': r => r.status === 200 });
  });

  sleep(1);
}

export function handleSummary(data) {
  return { 'docs/perf-report.json': JSON.stringify(data, null, 2) };
}
```

`scripts/run-perf.sh`:
```bash
docker run --rm --network host \
  -v $PWD/scripts/k6:/scripts \
  -v $PWD/docs:/docs \
  -e BASE_URL=http://localhost:8000 \
  grafana/k6:0.50.0 run /scripts/load.js
```

Çıktı: `docs/perf-report.json` + console’da p95 değeri. **Raporda:** `docs/final-report.md` içine p95 ekran görüntüsü.

**Kabul:**
- `bash scripts/run-perf.sh` → "✓ thresholds passed".
- p95 < 500ms (lokal dev’de gerçekçi).

**Alternatif: Locust** (`scripts/locustfile.py`) — k6’yı seçtiysek bunu yine de skeleton olarak bırakabiliriz. Rubric "k6 **veya** Locust" diyor; ikisinden biri yeterli.

## Görev 1.5 — Dokümantasyon (1.5 saat)

`README.md` (1. sayfa, kapak):
- [ ] Proje adı + 1 paragraf özet.
- [ ] Mimari görsel (`docs/architecture.png`).
- [ ] **Hızlı başlangıç:**
  ```bash
  docker compose up -d
  open http://localhost:8000/ui/
  open http://localhost:3000          # Grafana
  ```
- [ ] **Test komutları:** pytest, newman, playwright, k6 (her biri tek satır).
- [ ] **Endpoint tablosu** (api-contract özet).
- [ ] **Rubric karşılama checklist** (14 kalem, ✅ ile).
- [ ] Lisans + AI kullanımı notu.

`docs/architecture.md`:
- [ ] Mermaid diyagram (verdiğiniz görselin yenisi):
  ```mermaid
  flowchart TB
    GH[GitHubActions] --> Lint --> Test --> Docker --> Deploy --> Smoke
    Smoke --> Newman
    
    subgraph App [FastAPI]
      API
      PnL[PnLService]
      S3svc[S3Service]
    end
    
    API --> Postgres[(PostgreSQL_Testcontainers)]
    S3svc --> LocalStack[(LocalStack_S3)]
    
    K6 --> API
    Playwright --> UI[StaticUI]
    UI --> API
    
    API -->|/metrics| Prom[Prometheus]
    Prom --> Grafana
  ```
- [ ] Her bileşen için 1 paragraf: ne yapıyor, neden seçildi.
- [ ] Veri akışı senaryosu: "Kullanıcı SELL trade gönderirse ne olur?" (UI → router → service → DB → metrics → Grafana).

`docs/final-report.md` (4-6 sayfa, rubric kalemi):
- [ ] **Bölüm 1: Proje özeti** (yarım sayfa).
- [ ] **Bölüm 2: Mimari kararlar** (1 sayfa) — neden FastAPI, neden PostgreSQL, neden LocalStack.
- [ ] **Bölüm 3: Test stratejisi** (1 sayfa) — test piramidi, coverage %X, Testcontainers neden.
- [ ] **Bölüm 4: CI/CD ve dağıtım** (1 sayfa) — 5 job, Newman, K8s manifestleri.
- [ ] **Bölüm 5: Gözlem ve performans** (1 sayfa) — p95 sonuçları, Grafana ekran görüntüleri, 3 panel açıklaması.
- [ ] **Bölüm 6: Zorluklar ve öğrenimler** (yarım sayfa) — Decimal, async/sync, AI kullanımı.
- [ ] **Ek: Komut referansı** + repo linki.

`docs/demo-script.md` (sunum için):
- [ ] 10 dakikalık demo planı: mimari → kod → testler → CI → demo → sayılar.
- [ ] Soru-cevap için hazır cevaplar (P&L formülü, p95 nedir, Testcontainers neden).

`LICENSE`:
- [ ] MIT (template, GitHub web’den kopyala-yapıştır, yıl + isim doldur).

`docs/screenshots/`:
- [ ] `ui-portfolio.png`, `ui-summary.png`
- [ ] `grafana-panel-rps.png`, `grafana-panel-latency.png`, `grafana-panel-errors.png`
- [ ] `newman-success.png`
- [ ] `k6-thresholds.png`
- [ ] `ci-green.png`

**Kabul:** `docs/` dizini hazır, README açılıyor, mimari diyagram render ediliyor (GitHub Mermaid native).

## Görev 1.6 — integration.md sync (zorunlu, 10 dk)

- [ ] OKUMA PROTOKOLÜ.
- [ ] YAZMA PROTOKOLÜ ile entry:
  - **Başlık:** `agent3 sprint-1 ui+e2e+monitoring+perf+docs`
  - **Etkilenen noktalar:** B (prometheus/grafana servisleri eklendi), E (`pyproject.toml` `e2e` extra, `app/main.py` `/ui` mount aktive, `ci.yml` test job’a playwright step), F (Grafana 3 panel query’si metric adlarını kullanıyor), K (`static/`, `tests/e2e/`, `monitoring/`, `scripts/k6/`, `docs/` ürünleri).
  - **agent2 için not:** `ci.yml` test job’una eklediğim adımları kırmadan, `docker` ve `newman` job’larını koşturmaya devam edebilmelisin.
  - **agent1 için not:** UI mount’u `static/index.html` olmadan açma — sıralama korundu.
  - **Doğrulama komutu:** `pytest tests/e2e && bash scripts/run-perf.sh && curl localhost:9090/-/ready && curl localhost:3000/api/health`.
  - **Bağlı GATE:** `agent3 GATE-1`, `agent3 GATE-2`, `agent3 GATE-3` → `[x]`.

**Sprint 1 DoD:**
- ✅ UI 3 sayfa çalışıyor (`/ui/`)
- ✅ Playwright 5 senaryo yeşil
- ✅ Prometheus + Grafana stack ayakta, 3 panel veri gösteriyor
- ✅ k6 raporu `p(95)<500ms` PASS, `docs/perf-report.json` artifact
- ✅ README + mimari + final-report (4 sayfa minimum) commit
- ✅ LICENSE eklendi
- ✅ `docs/integration.md` Work Note eklendi, GATE-1/2/3 bildirildi
- ✅ Commit: `feat(quality): sprint-1 ui+e2e+monitoring+perf+docs`

---

# SPRINT 2 — Sağlamlaştırma (Gün 2)

## Görev 2.1 — Daha fazla E2E

- [ ] 2 senaryo daha ekle:
  - Çoklu portföy arasında geçiş.
  - Sayfa yenilendiğinde state korunuyor (refresh testi).
- [ ] `playwright trace + video` (failure’da artifact).
- [ ] Cross-browser: chromium + firefox + webkit (CI matrix).

## Görev 2.2 — k6 soak + stress

`scripts/k6/soak.js`:
- [ ] 30 dakika, sabit 50 VU.
- [ ] Memory leak / DB connection pool tükenmesi var mı kontrol.
- [ ] Grafana’da bu süre boyunca panel kaydı (sunumda gösterim).

## Görev 2.3 — Grafana zenginleştirme

- [ ] 4. panel: HTTP status code dağılımı (2xx/4xx/5xx pie).
- [ ] 5. panel: Top 5 endpoint (latency).
- [ ] Alert: `error_rate > 5% for 2m` → console log (production’da Alertmanager).

## Görev 2.4 — Belgeler sürümleme

- [ ] `docs/final-report.md` → 6 sayfaya çıkar.
- [ ] Performans grafiği eklemeleri.
- [ ] CHANGELOG.md (semantic versioning).
- [ ] AI kullanımı detaylı tablo: hangi kod hangi prompt’la üretildi (rubric “her satırı savun”).

## Görev 2.5 — integration.md sync

- [ ] OKUMA → YAZMA. Entry: `agent3 sprint-2 hardening`. Yeni panel/metric eklediysen Bölüm F’ye **bloker olarak öner**.

**Sprint 2 DoD:**
- ✅ 7+ E2E senaryo, 3 browser
- ✅ k6 soak rapor
- ✅ Grafana 5 panel
- ✅ Final rapor 6 sayfa
- ✅ `integration.md` Work Note eklendi

---

# SPRINT 3 — Phase 2 + Bonus (Gün 3)

## Görev 3.1 — Gemini analiz UI panel

- [ ] `static/summary.html` altına `<div id="ai-analysis">` ekle.
- [ ] Buton: "Bugünün analizini al" → `POST /portfolios/{id}/analysis/daily`.
- [ ] Response’u markdown render et (`marked.js` CDN, basit).
- [ ] Playwright senaryosu: butona tıkla → 30 sn içinde metin gelir (gerçek API yerine mock backend).

## Görev 3.2 — Midas fiyat panelini Grafana’ya bağla

- [ ] Custom counter: `midas_api_calls_total`, `midas_cache_hits_total` (Agent 1 servisinde).
- [ ] Grafana paneli: Midas hit/miss oranı.

## Görev 3.3 — OpenTelemetry tracing (Bonus +5)

- [ ] `opentelemetry-instrumentation-fastapi` paketini ekle.
- [ ] Jaeger compose’a ekle, trace’ler `/portfolios/{id}/summary` üzerinde görünür.
- [ ] Final raporda 1 paragraf.

## Görev 3.4 — integration.md sync

- [ ] OKUMA → YAZMA. Entry: `agent3 sprint-3 phase2 ui+midas-panel`.
  - Bölüm D.9 endpoint’i UI üzerinden tüketiyor; agent1 Phase 2’nin canlı olduğunu doğrula.
  - Bölüm F: Midas metric panel’i Grafana’da canlı.
  - (Bonus) OpenTelemetry Jaeger eklendiyse Bölüm B’ye yeni servis bloker olarak öner.

**Sprint 3 DoD:**
- ✅ UI’da Gemini paneli çalışıyor
- ✅ Grafana’da Midas paneli + (opsiyonel) Jaeger trace
- ✅ Bonus puan +5/+10
- ✅ `integration.md` Work Note eklendi
- ✅ Commit: `feat(phase2): ai analysis ui + midas observability`

---

## Komut özet kartı (Agent 3)

```bash
# UI
uvicorn app.main:app --reload
# tarayıcı: http://localhost:8000/ui/

# Playwright
playwright install chromium
pytest tests/e2e --headed              # debug
pytest tests/e2e -v                    # CI modu
pytest tests/e2e --tracing on          # trace artifact

# Monitoring
docker compose up -d prometheus grafana
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000 (admin/admin)

# k6 (Docker)
bash scripts/run-perf.sh
# veya direkt: k6 run scripts/k6/load.js

# Locust (alternatif)
locust -f scripts/locustfile.py --host http://localhost:8000

# Mermaid render (lokal)
npx @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/architecture.png

# Final rapor önizleme
npx markdown-pdf docs/final-report.md
```

---

## Risk / dikkat noktaları

1. **`static/` mount timing:** Agent 1 `main.py`’deki mount satırını sen aktive ediyorsun; ondan ÖNCE `static/index.html` mevcut olmalı, yoksa FastAPI startup’ta hata.
2. **`data-testid`:** Tüm interaktif elementlerde olsun, CSS class’larıyla test seçimi kırılgan.
3. **Grafana provisioning:** Dashboard JSON’u export ettikten sonra `id: null` ve `uid` set olmalı, yoksa Grafana her seferinde duplicate açar.
4. **Prometheus scrape:** `prometheus-fastapi-instrumentator` default olarak `http_requests_total` ve `http_request_duration_seconds` üretir; **bunlar dashboard query’lerinin tam ismi**, başka isim kullanma.
5. **k6 thresholds:** `p(95)<500` çok cömert; lokal SQLite’ta 50ms civarında olur. CI runner’da PostgreSQL ile 200-300ms beklenebilir. Threshold’u gevşek bırak, raporda gerçek değeri yaz.
6. **Playwright in CI:** `playwright install --with-deps` `apt-get install`’ı tetikler; `actions/setup-python` cache’i ile uyumlu.
7. **Final rapor 4-6 sayfa:** Markdown’da sayfa sayısı tahmini için ~500 kelime/sayfa hedefle.
8. **AI savunması:** Sunumda “her satırı savun” deniyor; AI ile üretilen kodları kendin satır satır okuyup yorum yazmazsan sunumda batırırsın. Final raporda “AI kullanımı” bölümünü ciddiye al.
