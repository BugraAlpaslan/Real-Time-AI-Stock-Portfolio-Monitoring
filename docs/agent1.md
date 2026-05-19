# Agent 1 — Backend Core + Test Coverage

> ## ⚠ ZORUNLU: integration.md PROTOKOLÜ
>
> Aşağıdaki adımlardan **herhangi birine başlamadan ÖNCE** [docs/integration.md](integration.md) dosyasını **OKUMA PROTOKOLÜ** ile oku (oku → 1 sn bekle → tekrar oku → eşitse devam).
>
> Aşağıdaki **entegrasyon noktalarına dokunduğun her seferde** [docs/integration.md](integration.md)’nin `Work Notes` bölümüne **YAZMA PROTOKOLÜ** ile entry ekle (üst kilit → 1 sn → kontrol → yaz → alt imza → kilit sil):
> - `app/main.py` üzerindeki paylaşılan TODO satırları (export router, /ui mount).
> - `pyproject.toml`’a yeni dependency ekleme.
> - `DATABASE_URL`, `S3_BUCKET`, `MIDAS_BASE_URL`, `GEMINI_API_KEY` env değişkenleri.
> - Yeni API endpoint sözleşmesi (`docs/integration.md` Bölüm D).
> - Prometheus metric adlarını değiştirme (Bölüm F — yasak, sadece ekleme).
> - Test marker’ı tanımlama (Bölüm I).
>
> **Katalog bölümlerini (A-K) doğrudan editleme**; bunun yerine `integration.md` → `🚨 Bloker` bölümüne yaz, orkestratör güncellesin.

---

> **Rol:** Tüm domain kodunu (FastAPI app, P&L servisi, modeller, DB) ve **pytest tabanlı testleri** yazar. Şartnamedeki **5 katmanı** tek başına kapatır: Mini Servis, Pytest, Veritabanı (+Testcontainers), Test Verisi, Coverage.
>
> **Hedef:** Sprint 1 sonunda `pytest --cov=app` çıktısı **≥ %70**, ≥ 3 integration test, ≥ 2 Testcontainers testi yeşil.

---

## 1. Sahip olduğu dosyalar (yalnız Agent 1 dokunur)

```
app/
├── __init__.py
├── main.py
├── database.py
├── config.py
├── models/
│   ├── __init__.py
│   └── models.py
├── schemas/
│   ├── __init__.py
│   └── schemas.py
├── services/
│   ├── __init__.py
│   └── portfolio_service.py
└── routers/
    ├── __init__.py
    ├── portfolios.py
    ├── trades.py
    └── health.py

tests/
├── __init__.py
├── conftest.py
├── factories.py
├── unit/
│   ├── __init__.py
│   ├── test_portfolio_service.py
│   ├── test_schemas.py
│   ├── test_models.py
│   └── test_factories.py
└── integration/
    ├── __init__.py
    ├── test_portfolio_endpoints.py
    ├── test_trade_flow.py
    ├── test_summary_endpoint.py
    ├── test_postgres_crud.py          # Testcontainers
    └── test_postgres_trade_flow.py    # Testcontainers

pyproject.toml         # bağımlılıklar + pytest + coverage config
.coveragerc            # (opsiyonel, pyproject yerine)
.python-version
```

**Diğer agent’lara dokunulan yerler (yalnızca tek satır):**
- `app/main.py` içine Agent 3 için `app.mount("/ui", StaticFiles(...))` placeholder satırı ve `Instrumentator().instrument(app).expose(app)` çağrısı eklenir.
- Agent 2’nin `app/routers/export.py` ve `app/services/s3_service.py` dosyalarını ekleyebilmesi için `main.py`’de `from app.routers import portfolios, trades, health, export` import’u **TODO** olarak hazırlanır.

---

## 2. Bağımlılıklar

| Kim’den | Ne | Ne zaman |
|---------|----|----------|
| — | Yok, ilk başlayan agent | Sprint 1 Gün 0 |
| → Agent 2 | `app.main:app` çalışır halde + `/health` 200 dönmeli | Sprint 1 sonu |
| → Agent 3 | Static dosyalar için `/ui` mount + `/metrics` exposed | Sprint 1 sonu |

**Engelleyici:** Yok. Agent 1, Sprint 0 olarak `docs/api-contract.md` üretir ve commit eder. Diğer iki agent bu dosyayı bekler.

---

## 3. API sözleşmesi (Sprint 0 çıktısı — `docs/api-contract.md`)

| # | Method | Path | Request body | Response | Status |
|---|--------|------|--------------|----------|--------|
| 1 | POST | `/portfolios` | `{name, description?, currency}` | `PortfolioOut` | 201 |
| 2 | GET | `/portfolios/{id}` | — | `PortfolioOut` (+ pozisyonlar) | 200/404 |
| 3 | POST | `/portfolios/{id}/trades` | `{ticker, trade_type, quantity, price, commission?, notes?}` | `TradeOut` | 201/400/404 |
| 4 | GET | `/portfolios/{id}/trades` | `?ticker=&limit=` | `list[TradeOut]` | 200 |
| 5 | GET | `/portfolios/{id}/summary` | — | `SummaryOut` (realized + unrealized + total) | 200 |
| 6 | GET | `/health` | — | `{status:"ok", db:"up"}` | 200 |
| 7 | GET | `/metrics` | — | Prometheus exposition | 200 |

**Hata modeli:** FastAPI `HTTPException` + RFC 7807 benzeri `{detail, code}`.

**P&L kuralları (Servis):**
- BUY → pozisyon `quantity += q`; `average_cost = (eski_q*eski_avg + q*price + commission) / yeni_q`.
- SELL → pozisyonda yeterli adet yoksa `400 INSUFFICIENT_POSITION`. Yeterli ise:
  - `realized_pnl += (price - average_cost) * q - commission`
  - `quantity -= q` (sıfır olunca pozisyon silinmez, tutulur, history için)
- `unrealized_pnl = Σ (current_price - average_cost) * quantity`
  - Phase 1: `current_price = son trade fiyatı (aynı ticker)` veya `average_cost` (yoksa 0).
  - Phase 2 (Agent 1 Sprint 3): Midas servisinden çekilir.

---

# SPRINT 1 — MVP + Full Coverage (Gün 0 – Gün 1)

> **Çıkış kriteri:** `pytest --cov=app --cov-fail-under=70` → ✅ yeşil. ≥3 integration + ≥2 Testcontainers testi yeşil. `uvicorn app.main:app` → `/docs` açılır.

## Görev 1.1 — Proje iskeleti ve bağımlılıklar (30 dk)

- [ ] `pyproject.toml` oluştur. Bölümler:
  ```toml
  [project]
  name = "stock-portfolio-tracker"
  version = "0.1.0"
  requires-python = ">=3.11"
  dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy>=2.0",
    "psycopg2-binary>=2.9",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "alembic>=1.13",
    "prometheus-fastapi-instrumentator>=7.0",
    "boto3>=1.34",
    "httpx>=0.27",
  ]

  [project.optional-dependencies]
  dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-asyncio>=0.23",
    "factory-boy>=3.3",
    "faker>=24.0",
    "testcontainers[postgres]>=4.0",
    "ruff>=0.4",
    "mypy>=1.10",
    "freezegun>=1.5",
  ]

  [tool.pytest.ini_options]
  testpaths = ["tests"]
  addopts = "-ra -q --strict-markers"
  markers = ["integration: integration tests", "testcontainers: requires docker"]

  [tool.coverage.run]
  source = ["app"]
  omit = ["app/main.py", "app/__init__.py"]

  [tool.coverage.report]
  fail_under = 70
  show_missing = true
  skip_covered = false
  exclude_lines = ["if __name__", "pragma: no cover", "raise NotImplementedError"]

  [tool.ruff]
  line-length = 100
  target-version = "py311"
  ```
- [ ] `.python-version` → `3.11.9`.
- [ ] `python -m venv .venv` + `pip install -e ".[dev]"` çalıştığını doğrula.

**Kabul:** `pip install -e ".[dev]"` 0 hata.

## Görev 1.2 — Config + database katmanı (30 dk)

- [ ] `app/config.py`: `pydantic-settings.BaseSettings`
  - `database_url: str = "sqlite:///./portfolio.db"`
  - `aws_endpoint_url: str | None = None` (LocalStack için Agent 2)
  - `gemini_api_key: str | None = None` (Phase 2)
  - `midas_base_url: str = "https://www.getmidas.com/wp-json/midas-api/v1"`
  - `env: Literal["dev","test","prod"] = "dev"`
- [ ] `app/database.py`:
  - `engine = create_engine(settings.database_url, connect_args=... if sqlite else {})`
  - `SessionLocal = sessionmaker(...)`
  - `Base = declarative_base()`
  - `def get_db()` generator
  - `def init_db()` `Base.metadata.create_all(engine)`

**Kabul:** `python -c "from app.database import init_db; init_db()"` hatasız.

## Görev 1.3 — SQLAlchemy modelleri (45 dk)

`app/models/models.py`:

- [ ] `class TradeType(str, enum.Enum)` → `BUY`, `SELL`.
- [ ] `class Portfolio(Base)`:
  - `id, name(unique=True), description, currency, created_at, updated_at`
  - `positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")`
  - `trades   = relationship("Trade",    back_populates="portfolio", cascade="all, delete-orphan")`
- [ ] `class Position(Base)`:
  - `id, portfolio_id(FK), ticker, quantity(Numeric(20,4)), average_cost(Numeric(20,4)), realized_pnl(Numeric(20,4), default=0)`
  - `UniqueConstraint(portfolio_id, ticker)`
- [ ] `class Trade(Base)`:
  - `id, portfolio_id(FK), ticker, trade_type(Enum), quantity, price, commission, notes, executed_at(default=now)`
  - Index: `(portfolio_id, ticker, executed_at)`.

**Kabul:** `Base.metadata.create_all()` SQLite ve PG’de sorunsuz; tablolar oluşur.

## Görev 1.4 — Pydantic şemaları (30 dk)

`app/schemas/schemas.py` (Pydantic v2):

- [ ] `PortfolioCreate`, `PortfolioOut`, `PortfolioWithPositions`.
- [ ] `TradeCreate` (validator: `quantity > 0`, `price > 0`, `commission >= 0`).
- [ ] `TradeOut`.
- [ ] `PositionOut` (+ `unrealized_pnl` computed field — schemada **değil**, summary endpoint’inde hesaplanır).
- [ ] `SummaryOut`: `total_cost, total_market_value, realized_pnl, unrealized_pnl, total_pnl, positions: list[PositionWithMarket]`.

**Kabul:** `python -c "from app.schemas.schemas import *"` hatasız.

## Görev 1.5 — P&L servis katmanı (1 saat)

`app/services/portfolio_service.py`. **En kritik dosya. Coverage’ın çekirdeği.**

Sınıf veya modül fonksiyonları:

- [ ] `create_portfolio(db, payload) -> Portfolio`
- [ ] `get_portfolio(db, id) -> Portfolio` (404 → `HTTPException`)
- [ ] `add_trade(db, portfolio_id, payload) -> Trade`:
  - Portföyü kilitle (`with_for_update()`, PG’de gerçek, SQLite’ta no-op).
  - Mevcut pozisyonu getir veya yarat.
  - BUY/SELL mantığını uygula (yukarıdaki formüller).
  - `db.flush()` + `db.refresh()`.
- [ ] `list_trades(db, portfolio_id, ticker=None, limit=50) -> list[Trade]`
- [ ] `compute_summary(db, portfolio_id, price_provider=None) -> SummaryOut`:
  - `price_provider` opsiyonel callable; default → son trade fiyatı.
  - Bu, Phase 2’de Midas’ı **dependency injection** ile bağlamayı kolaylaştırır.

**Hata yolları:**
- Insufficient position → `ValueError("INSUFFICIENT_POSITION")` (router 400’e çevirir).
- Bilinmeyen portföy → `LookupError` (router 404’e çevirir).

**Kabul:** Bu modülün her satırı unit test ile kapsanmalı (`coverage report -m` → 0 missing).

## Görev 1.6 — Router’lar (45 dk)

- [ ] `app/routers/portfolios.py`:
  - `POST /portfolios`, `GET /portfolios/{id}`, `GET /portfolios/{id}/summary`.
  - `Depends(get_db)` ile session.
- [ ] `app/routers/trades.py`:
  - `POST /portfolios/{id}/trades`, `GET /portfolios/{id}/trades`.
  - `try/except ValueError` → `HTTPException(400, code="INSUFFICIENT_POSITION")`.
- [ ] `app/routers/health.py`:
  - `GET /health` → DB ping (`SELECT 1`).

**Kabul:** Tüm rotalar `/docs` Swagger UI’da görünür.

## Görev 1.7 — `app/main.py` (15 dk)

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import init_db
from app.routers import portfolios, trades, health
# from app.routers import export  # Agent 2, Sprint 1.4'te dolduracak

app = FastAPI(title="Stock Portfolio Tracker", version="0.1.0")

@app.on_event("startup")
def _startup():
    init_db()

app.include_router(health.router, tags=["health"])
app.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])
app.include_router(trades.router, prefix="/portfolios", tags=["trades"])
# app.include_router(export.router, prefix="/portfolios", tags=["export"])  # Agent 2

Instrumentator().instrument(app).expose(app)  # /metrics — Agent 3 buraya scrape edecek

# Agent 3, Sprint 1.1'de static/ klasörünü oluşturduktan sonra aşağıdaki satır aktive olur:
# app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")
```

**Kabul:** `uvicorn app.main:app --reload` çalışır. `/docs`, `/metrics`, `/health` 200.

## Görev 1.8 — `tests/conftest.py` + factories session wiring (45 dk)

`tests/conftest.py`:

- [ ] In-memory SQLite engine (StaticPool + `connect_args={"check_same_thread": False}`).
- [ ] `db_session` fixture: her testte fresh schema + transaction rollback.
- [ ] `client` fixture: `TestClient(app)` + `app.dependency_overrides[get_db] = lambda: db_session`.
- [ ] `factories.PortfolioFactory._meta.sqlalchemy_session = db_session` (autouse).

`tests/factories.py` (mesajınızdaki kod + iyileştirmeler):

- [ ] `PortfolioFactory`, `TradeFactory`, `BuyTradeFactory`, `SellTradeFactory`, `PositionFactory`.
- [ ] `with_trades(n=5)` helper (`PortfolioFactory.create_batch` + `TradeFactory.create_batch`).

**Kabul:** `pytest tests/unit/test_factories.py` ile en az 3 factory testi yeşil.

## Görev 1.9 — Unit testler (1.5 saat) — **coverage’ın %60’ı buradan**

`tests/unit/test_portfolio_service.py` (en az 15 test):

- [ ] `test_create_portfolio_persists`
- [ ] `test_get_portfolio_not_found_raises`
- [ ] `test_buy_creates_position`
- [ ] `test_buy_existing_position_updates_average_cost` (sayısal doğrulama: 10@100 + 10@120 → avg=110)
- [ ] `test_buy_average_cost_includes_commission`
- [ ] `test_sell_reduces_quantity`
- [ ] `test_sell_realized_pnl_calculation` (100@100 al, 50@120 sat → realized=1000-comm)
- [ ] `test_sell_insufficient_raises_value_error`
- [ ] `test_sell_on_missing_position_raises`
- [ ] `test_list_trades_filtered_by_ticker`
- [ ] `test_list_trades_limit_respected`
- [ ] `test_summary_no_positions_returns_zero`
- [ ] `test_summary_unrealized_with_last_trade_price`
- [ ] `test_summary_total_pnl_sums_realized_and_unrealized`
- [ ] `test_summary_with_custom_price_provider` (lambda ticker: 999) → DI doğrulaması

`tests/unit/test_schemas.py` (en az 6 test):

- [ ] Negatif quantity reddi, negatif price reddi, geçersiz trade_type, default currency, missing name.

`tests/unit/test_models.py` (en az 3 test):

- [ ] `UniqueConstraint(portfolio_id, ticker)` ihlal → IntegrityError.
- [ ] Cascade delete: portfolio silinince trades & positions siliniyor mu.
- [ ] TradeType enum string serialization.

`tests/unit/test_factories.py` (en az 4 test):

- [ ] PortfolioFactory tek instance.
- [ ] BuyTradeFactory `trade_type == BUY`.
- [ ] `create_batch(10)` benzersiz ticker dağılımı.
- [ ] PositionFactory referans bütünlüğü.

**Kabul:** `pytest tests/unit -v` tüm testler yeşil. `pytest --cov=app/services --cov=app/models --cov=app/schemas` → her biri **≥ %90**.

## Görev 1.10 — Integration testler (1 saat) — **3+ zorunlu**

`tests/integration/test_portfolio_endpoints.py`:

- [ ] `test_create_portfolio_201`
- [ ] `test_get_portfolio_with_positions`
- [ ] `test_get_portfolio_404`
- [ ] `test_health_returns_db_up`

`tests/integration/test_trade_flow.py`:

- [ ] `test_buy_then_sell_realized_pnl_visible_in_summary`
- [ ] `test_sell_insufficient_returns_400_with_code`
- [ ] `test_list_trades_after_multiple_buys`

`tests/integration/test_summary_endpoint.py`:

- [ ] `test_summary_aggregates_multi_ticker_pnl`
- [ ] `test_summary_zero_for_empty_portfolio`

**Kabul:** `pytest tests/integration -m "not testcontainers"` yeşil.

## Görev 1.11 — Testcontainers testleri (45 dk) — **2+ zorunlu**

`tests/integration/test_postgres_crud.py`:

```python
@pytest.fixture(scope="module")
def pg_url():
    from testcontainers.postgres import PostgresContainer
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()
```

- [ ] `test_postgres_create_and_query_portfolio` (gerçek PG’de unique constraint).
- [ ] `test_postgres_concurrent_trades_consistency` (iki session aynı portföye yazıyor).

`tests/integration/test_postgres_trade_flow.py`:

- [ ] `test_postgres_full_buy_sell_flow_realized_pnl`
- [ ] `test_postgres_summary_endpoint_with_real_pg`

**Kabul:** `pytest -m testcontainers` Docker çalışırken yeşil. CI’da Docker servisi açık olmalı (Agent 2 ayarlar).

## Görev 1.12 — Coverage’ı %70’in üstüne çıkar (30 dk)

- [ ] `pytest --cov=app --cov-report=term-missing` çalıştır, kırmızı satırları gör.
- [ ] Eksik satırlar için **targeted** unit test ekle (genellikle hata yolları: `except` blokları, 404, 400).
- [ ] `pyproject.toml` → `fail_under = 70` ekle.
- [ ] `pytest --cov-fail-under=70` lokal yeşil.

## Görev 1.13 — integration.md sync (zorunlu, 10 dk)

- [ ] `docs/integration.md` → OKUMA PROTOKOLÜ ile oku.
- [ ] YAZMA PROTOKOLÜ ile `Work Notes`’a entry ekle:
  - **Başlık:** `agent1 sprint-1 backend + 70% coverage`
  - **Etkilenen noktalar:** D.1–D.7 (endpoint’ler aktive), A.`DATABASE_URL`/`ENV`, I.`integration`+`testcontainers` marker’ları, K.`app/`, K.`tests/`, F.`http_requests_*` metric’leri canlı.
  - **Doğrulama komutu:** `pytest --cov=app --cov-fail-under=70 && uvicorn app.main:app --port 8000` + `curl localhost:8000/health`.
  - **Bağlı GATE:** `agent1 GATE-1`, `agent1 GATE-2`, `agent1 GATE-3` → `[x]`.
- [ ] GATE’leri `[ ]` → `[x]` olarak kendi entry’nde belirt. (Katalog tablosundaki checkbox’ı yalnız orkestratör günceller — sen sadece bildir.)

**Sprint 1 Definition of Done:**
- ✅ `uvicorn app.main:app` çalışır
- ✅ `/docs` Swagger 7 endpoint gösterir
- ✅ `pytest` 30+ test, hepsi yeşil
- ✅ `pytest --cov=app --cov-fail-under=70` ✅
- ✅ `tests/factories.py` çalışır (Agent 1’in mesajdaki kodu uyumlu)
- ✅ Testcontainers ile 2 PG testi yeşil
- ✅ `docs/integration.md` Work Notes entry eklendi, GATE-1/2/3 bildirildi
- ✅ Git commit: `feat(backend): sprint-1 core domain + 70% coverage`

---

# SPRINT 2 — Sağlamlaştırma (Gün 2, yarım gün)

> **Hedef:** Coverage %85+, ruff/mypy temiz, edge case’ler kapalı, CI’da sürekli yeşil.

## Görev 2.1 — Lint + type-check temizliği

- [ ] `ruff check app tests --fix` → 0 hata.
- [ ] `mypy app` → 0 hata (gerekirse `# type: ignore[no-redef]` yerine düzelt).
- [ ] `ruff format` ile tek tip stil.

## Görev 2.2 — Coverage push (%70 → %85+)

- [ ] `coverage report -m` rapor sonu eksik satırlar listesi:
  - Router’larda except yolları: `test_*_db_error_returns_500`.
  - `compute_summary` price_provider hata fırlatırsa fallback.
- [ ] Property-based test (opsiyonel): `hypothesis` ile rastgele trade sekansı → P&L invariant `Σ realized + (mkt - cost) = total_pnl`.

## Görev 2.3 — Negative / boundary testler

- [ ] Decimal precision: 0.0001 quantity nasıl işleniyor.
- [ ] Çok büyük sayı: `quantity = 1e9` overflow olmuyor.
- [ ] Aynı anda 2 trade gönderildiğinde idempotency? (en azından dokumentleyin).
- [ ] SQL injection denemesi (FastAPI param binding ile zaten korunmalı, doğrula).

## Görev 2.4 — Alembic migration (opsiyonel ama önerilir)

- [ ] `alembic init migrations`.
- [ ] `alembic revision --autogenerate -m "init"`.
- [ ] CI’da migrate adımı.

## Görev 2.5 — integration.md sync

- [ ] OKUMA PROTOKOLÜ → YAZMA PROTOKOLÜ.
- [ ] Entry: `agent1 sprint-2 hardening`. Yeni test marker eklediysen Bölüm I’ya, yeni env eklediysen Bölüm A’ya **bloker** olarak yaz.

**Sprint 2 DoD:**
- ✅ Coverage ≥ %85
- ✅ `ruff` + `mypy` 0 hata
- ✅ 40+ test, tümü yeşil
- ✅ `integration.md` Work Note eklendi
- ✅ Commit: `chore(backend): sprint-2 hardening + 85% coverage`

---

# SPRINT 3 — Phase 2: Midas + Gemini entegrasyonu (Gün 3)

> **Şartname dışı, bonus.** Sırf Agent 1’in dokunduğu kısımlar burada.

## Görev 3.1 — `app/services/midas_price_service.py`

- [ ] `class MidasPriceService`:
  - `__init__(self, base_url, http_client=None, ttl_seconds=300)`
  - `get_price(ticker: str) -> Decimal | None`
  - In-memory TTL cache (`functools.lru_cache` yerine manuel dict + timestamp).
- [ ] `compute_summary` çağrısında `price_provider = midas_service.get_price` enjekte et.
- [ ] Test: `respx` veya `httpx.MockTransport` ile Midas yanıtını mockla. **3 test** (success, ticker yok, timeout fallback).

## Görev 3.2 — `app/services/gemini_analysis_service.py`

- [ ] `class GeminiAnalysisService`:
  - `analyze_portfolio(summary: SummaryOut, trades: list[TradeOut]) -> str`
  - Prompt template: pozisyonlar + son 10 trade + P&L → Türkçe günlük yorum.
  - `google-generativeai` paketi (`gemini-1.5-flash`).
- [ ] `POST /portfolios/{id}/analysis/daily` endpoint’i (router’a ekle).
  - Sonucu Agent 2’nin S3 servisine yazar (`s3_service.put_analysis(...)`).
- [ ] Test: Gemini’yi mock (sabit string döndür). LocalStack S3’e yazma testi (Testcontainers veya boto3 stub).

## Görev 3.3 — integration.md sync

- [ ] OKUMA PROTOKOLÜ → YAZMA PROTOKOLÜ.
- [ ] Entry: `agent1 sprint-3 phase2 midas+gemini`.
  - Bölüm A: `GEMINI_API_KEY` ve `MIDAS_BASE_URL` gerçek değerlerle kullanıldı.
  - Bölüm D: endpoint #9 (`POST /portfolios/{id}/analysis/daily`) aktive edildi.
  - Bölüm F: `midas_api_calls_total`, `midas_cache_hits_total` metric’leri canlı.
  - Bölüm G: `portfolio-analysis` bucket key’leri yazılıyor.
  - agent2 ve agent3 için **bloker yok / bloker var** ayrımını net yaz.

**Sprint 3 DoD:**
- ✅ `GET /portfolios/{id}/summary` Midas fiyatıyla unrealized P&L döner
- ✅ `POST /portfolios/{id}/analysis/daily` Gemini’den metin alır ve S3’e yazar
- ✅ Yeni servisler ≥ %80 coverage
- ✅ `integration.md` Work Note eklendi, agent2/agent3’e haber bırakıldı
- ✅ Commit: `feat(phase2): midas price + gemini daily analysis`

---

## Komut özet kartı (Agent 1)

```bash
# Kurulum
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"

# Çalıştır
uvicorn app.main:app --reload --port 8000

# Test
pytest                                            # tüm testler
pytest tests/unit -v                              # sadece unit
pytest -m "not testcontainers"                    # Docker olmadan
pytest -m testcontainers                          # PG container'lı
pytest --cov=app --cov-report=term-missing        # coverage
pytest --cov=app --cov-report=html                # HTML rapor → htmlcov/index.html
pytest --cov=app --cov-fail-under=70              # CI eşiği

# Kalite
ruff check app tests --fix
ruff format app tests
mypy app
```

---

## Risk / dikkat noktaları

1. **Decimal vs float:** SQLAlchemy `Numeric(20, 4)` kullan, Python tarafında `decimal.Decimal`. JSON serileştirmesinde Pydantic `Decimal` → string olarak verir; testlerde `Decimal("12.50") == 12.5` karşılaştırması doğrudur ama JSON karşılaştırırken dikkat.
2. **SQLite vs PG:** `with_for_update()` SQLite’ta no-op. Concurrency testi sadece PG container’da anlamlı.
3. **Factory session:** `conftest.py`’de her testten önce `PortfolioFactory._meta.sqlalchemy_session = db_session` set edilmeli; aksi halde testler arası leak olur.
4. **Coverage tuzakları:** `app/main.py` startup event’i ölçülmesi zor; `pyproject.toml` `omit` listesine ekledik.
5. **Agent 2 / Agent 3 ile uyum:** `main.py`’deki TODO satırlarını **silme**, diğer agent’lar bu noktaya yazacak.
