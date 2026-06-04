# TODO: Teknik İndikatör Sinyal Skoru → Gemini Analiz Tetikleyici + Telegram Bildirim

> **Kural:** Mevcut backend koduna (`app/routers/`, `app/services/portfolio_service.py`,
> `app/services/price_service.py`, `app/services/s3_service.py`, `app/models/`, `app/schemas/`)
> **dokunulmaz.** Her şey yeni, izole dosyalarda yapılır.
> `app/main.py` ve `pyproject.toml` yalnızca yeni router/paket eklemek için minimal olarak güncellenir.

---

## Genel Mimari

```
GET /portfolios/{id}/signals           ← Yeni endpoint (salt okunur, mevcut routerları etkilemez)
        │
        ▼
app/routers/signals.py                 ← Yeni router
        │
        ├──► app/services/signal_service.py
        │         ├── Fiyat geçmişini çeker (Yahoo Finance)
        │         ├── pandas-ta ile 4 indikatörü hesaplar
        │         ├── Her indikatöre puan atar (+1 / 0 / -1)
        │         └── Toplam skoru döner  →  SignalResult
        │
        └── [triggered=True ise sırayla:]
              │
              ├──► app/services/gemini_analysis_service.py
              │         ├── google-generativeai ile Gemini Flash
              │         └── Türkçe analiz metni üretir
              │
              └──► app/services/telegram_service.py
                        ├── Tetiklenme sebebini (hangi indikatörler aktif) formatlar
                        ├── Gemini metnini mesaja ekler
                        └── Telegram Bot API'ye HTTP POST gönderir
```

---

## Görev Listesi

### ADIM 0 — Hazırlık & Bağımlılık Kurulumu

- [ ] **0.1** `pyproject.toml` → `dependencies` listesine ekle:
  ```toml
  "pandas>=2.2",
  "pandas-ta>=0.3.14b",
  "google-generativeai>=0.7",
  "yfinance>=0.2",
  ```
  > `yfinance` — fiyat geçmişi için (günlük OHLCV). Mevcut `price_service.py`'daki anlık fiyat
  > çekme mantığından bağımsız; sadece sinyal servisi kullanır.
  > `httpx` zaten `pyproject.toml`'da mevcut — Telegram HTTP çağrıları için ayrıca eklemeye gerek yok.

- [ ] **0.2** Sanal ortama kur:
  ```powershell
  pip install pandas pandas-ta "google-generativeai>=0.7" yfinance
  ```

- [ ] **0.3** `.env.example`'a satır ekle (varsa `.env`'e de):
  ```
  GEMINI_API_KEY=your_key_here
  SIGNAL_SCORE_THRESHOLD=2
  TELEGRAM_BOT_TOKEN=your_bot_token_here
  TELEGRAM_CHAT_ID=your_chat_id_here
  ```
  > `SIGNAL_SCORE_THRESHOLD` — Gemini + Telegram'ın tetikleneceği minimum mutlak skor (varsayılan: 2).
  > `TELEGRAM_BOT_TOKEN` — BotFather'dan alınan token (`123456:ABC-DEF...` formatı).
  > `TELEGRAM_CHAT_ID` — Bildirimin gönderileceği chat/kanal ID'si (negatif sayı = grup/kanal).

- [ ] **0.4** `app/config.py` → `Settings` sınıfına **yalnızca dört alan ekle**
  (dosyanın geri kalanına dokunma):
  ```python
  signal_score_threshold: int = 2
  signal_history_days: int = 90        # kaç günlük OHLCV çekilsin
  telegram_bot_token: str | None = None
  telegram_chat_id: str | None = None
  ```
  > `gemini_api_key` zaten var — ekleme.

---

### ADIM 1 — Sinyal Servisi (`app/services/signal_service.py`)

> **Tamamen yeni dosya.** Hiçbir mevcut servisi import etmez, hiçbir mevcut servisi değiştirmez.

#### 1.1 Dosya iskeleti

```python
# app/services/signal_service.py
from __future__ import annotations

import pandas as pd
import pandas_ta as ta
import yfinance as yf

from app.config import settings


# ---------- Veri Katmanı ----------

def fetch_ohlcv(ticker: str, days: int = 90) -> pd.DataFrame:
    """
    Yahoo Finance'ten son `days` günlük OHLCV verisini çeker.
    Döner: open, high, low, close, volume sütunları olan DataFrame.
    Hata durumunda ValueError fırlatır.
    """
    ...


# ---------- İndikatör Hesaplama ----------

def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    pandas-ta ile RSI, MACD, Bollinger Bands, Stochastic hesaplar;
    sonuçları df'e sütun olarak ekler.
    Döner: genişletilmiş DataFrame.
    """
    ...


# ---------- Puanlama ----------

def _score_rsi(df: pd.DataFrame) -> int:
    """Son satır RSI değerini okur; ≤33 → +1, ≥67 → -1, arası → 0."""
    ...


def _score_macd(df: pd.DataFrame) -> int:
    """
    MACD kesişimi kontrol eder:
    Son satırda MACD > Sinyal VE bir önceki satırda MACD ≤ Sinyal → +1 (yukarı kesişim)
    Son satırda MACD < Sinyal VE bir önceki satırda MACD ≥ Sinyal → -1 (aşağı kesişim)
    """
    ...


def _score_bollinger(df: pd.DataFrame) -> int:
    """
    Fiyat, alt banda ≤ dokunuyorsa → +1
    Fiyat, üst banda ≥ dokunuyorsa → -1
    'Dokunma' toleransı: |fiyat - bant| / fiyat ≤ 0.005 (%0.5)
    """
    ...


def _score_stochastic(df: pd.DataFrame) -> int:
    """
    %K, %D'yi 20 seviyesinin altında yukarı kesiyorsa → +1
    %K, %D'yi 80 seviyesinin üzerinde aşağı kesiyorsa → -1
    """
    ...


# ---------- Ana Fonksiyon ----------

def compute_signal_score(ticker: str) -> SignalResult:
    """
    Dışarıya açık tek giriş noktası.
    Döner: SignalResult (pydantic modeli değil, dataclass/TypedDict).
    """
    ...
```

#### 1.2 Uygulanacak Detaylar

- [ ] **1.2.1** `fetch_ohlcv` — `yf.download(ticker, period=f"{days}d", interval="1d")` kullan.
  Boş DataFrame dönerse `ValueError(f"No OHLCV data for {ticker}")` fırlat.

- [ ] **1.2.2** `_compute_indicators` içinde pandas-ta çağrıları:
  ```python
  df.ta.rsi(length=14, append=True)           # RSI_14
  df.ta.macd(fast=12, slow=26, signal=9, append=True)  # MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
  df.ta.bbands(length=20, std=2, append=True)  # BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
  df.ta.stoch(k=14, d=3, smooth_k=3, append=True)  # STOCHk_14_3_3, STOCHd_14_3_3
  ```

- [ ] **1.2.3** `_score_rsi` — son satırı `df.iloc[-1]` ile oku, `RSI_14` sütununu kullan.
  NaN ise 0 dön.

- [ ] **1.2.4** `_score_macd` — son iki satırı `df.tail(2)` ile oku.
  `MACD_12_26_9` ve `MACDs_12_26_9` sütunlarını karşılaştır.
  Yeterli veri (≥ 2 satır) yoksa 0 dön.

- [ ] **1.2.5** `_score_bollinger` — `BBL_20_2.0` (alt), `BBU_20_2.0` (üst), kapanış fiyatı.
  Tolerans: `abs(close - band) / close <= 0.005`

- [ ] **1.2.6** `_score_stochastic` — son iki satır, `STOCHk_14_3_3`, `STOCHd_14_3_3`.
  Yukarı kesişim: önceki `k ≤ d` ve şimdiki `k > d` ve şimdiki `k < 20`
  Aşağı kesişim: önceki `k ≥ d` ve şimdiki `k < d` ve şimdiki `k > 80`

- [ ] **1.2.7** `SignalResult` — servis katmanında kullanmak için basit yapı:
  ```python
  from dataclasses import dataclass

  @dataclass
  class SignalResult:
      ticker: str
      rsi_score: int        # +1 / 0 / -1
      macd_score: int
      bollinger_score: int
      stochastic_score: int
      total_score: int      # rsi + macd + bollinger + stochastic
      rsi_value: float | None
      latest_close: float | None
      triggered: bool       # |total_score| >= settings.signal_score_threshold
  ```

- [ ] **1.2.8** `compute_signal_score` — adımları sırası ile çağırır, `SignalResult` doldurur.

---

### ADIM 2 — Gemini Analiz Servisi (`app/services/gemini_analysis_service.py`)

> **Tamamen yeni dosya.** `signal_service.py`'dan `SignalResult` alır; mevcut servislere dokunmaz.

#### 2.1 Dosya iskeleti

```python
# app/services/gemini_analysis_service.py
from __future__ import annotations

import google.generativeai as genai

from app.config import settings
from app.services.signal_service import SignalResult


def _build_prompt(result: SignalResult) -> str:
    """
    SignalResult verisini kullanarak Türkçe analiz prompt'u oluşturur.
    Sinyal skorlarını, indikatör değerlerini ve yönü açıkça belirtir.
    """
    ...


def generate_analysis(result: SignalResult) -> str:
    """
    Gemini Flash'ı çağırır, Türkçe analiz metni döner.
    GEMINI_API_KEY yoksa veya API hatası olursa boş string dön, exception fırlatma.
    """
    ...
```

#### 2.2 Uygulanacak Detaylar

- [ ] **2.2.1** `_build_prompt` çıktısı örneği:
  ```
  Sen bir finansal analiz asistanısın. Aşağıdaki teknik sinyal verilerine göre
  {ticker} hissesi için kısa Türkçe bir yorum yaz (maksimum 3 cümle):

  - RSI Skoru: {rsi_score} (RSI değeri: {rsi_value:.1f})
  - MACD Skoru: {macd_score}
  - Bollinger Bands Skoru: {bollinger_score}
  - Stochastic Skoru: {stochastic_score}
  - Toplam Sinyal Skoru: {total_score} (Eşik: ±{threshold})
  - Son Kapanış: {latest_close}

  Sinyal yönü: {"ALIM" if total_score > 0 else "SATIM"}
  ```

- [ ] **2.2.2** `generate_analysis`:
  ```python
  if not settings.gemini_api_key:
      return ""
  genai.configure(api_key=settings.gemini_api_key)
  model = genai.GenerativeModel("gemini-1.5-flash")
  response = model.generate_content(_build_prompt(result))
  return response.text
  ```
  - `try/except Exception` ile sarmalayıp hata durumunda `""` dön.

---

### ADIM 2.5 — Telegram Bildirim Servisi (`app/services/telegram_service.py`)

> **Tamamen yeni dosya.** `signal_service.py`'dan `SignalResult` ve Gemini analiz metnini alır.
> Dışarıya bağımlılığı yalnızca `httpx` (zaten kurulu) ve Telegram Bot API'dir.

#### 2.5.1 Dosya iskeleti

```python
# app/services/telegram_service.py
from __future__ import annotations

import httpx

from app.config import settings
from app.services.signal_service import SignalResult

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _build_trigger_reason(result: SignalResult) -> str:
    """
    Hangi indikatörlerin aktif olduğunu ve yönlerini açıklayan
    okunabilir Türkçe metin üretir.
    Örnek çıktı:
        🔴 RSI → SATIM sinyali (RSI: 71.2)
        🟢 MACD → ALIM sinyali (kesişim yukarı)
        ⚪ Bollinger → Nötr
        🔴 Stochastic → SATIM sinyali (%K > %D, seviye 80 üzeri)
    """
    ...


def _build_message(result: SignalResult, gemini_analysis: str) -> str:
    """
    Telegram mesajını Markdown formatında oluşturur.
    İçerir:
      - Başlık: hisse + yön (ALIM/SATIM) + toplam skor
      - Tetiklenme sebebi: _build_trigger_reason() çıktısı
      - Son kapanış fiyatı
      - Gemini analizi (varsa)
    """
    ...


def send_signal_notification(result: SignalResult, gemini_analysis: str) -> bool:
    """
    Dışarıya açık tek giriş noktası.
    Telegram Bot API'ye senkron HTTP POST gönderir.
    TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID yoksa sessizce False döner.
    Hata durumunda exception fırlatmaz, False döner.
    Başarıda True döner.
    """
    ...
```

#### 2.5.2 Uygulanacak Detaylar

- [ ] **2.5.2a** `_build_trigger_reason` — her indikatör skoru için:
  - `+1` → `🟢 {İndikatör} → ALIM sinyali ({detay})`
  - `-1` → `🔴 {İndikatör} → SATIM sinyali ({detay})`
  - `0`  → `⚪ {İndikatör} → Nötr`

  Detay alanları:
  | İndikatör | Detay içeriği |
  |-----------|--------------|
  | RSI | `RSI değeri: {rsi_value:.1f}` |
  | MACD | `kesişim {'yukarı' if score==+1 else 'aşağı'}` |
  | Bollinger | `fiyat {'alt' if score==+1 else 'üst'} banda yakın` |
  | Stochastic | `%K {'>' if score==-1 else '<'} %D, {'80' if score==-1 else '20'} seviyesi` |

- [ ] **2.5.2b** `_build_message` şablonu:
  ```
  📊 *{ticker} — {"🟢 ALIM" if total_score > 0 else "🔴 SATIM"} SİNYALİ*
  Toplam Skor: *{total_score}/{max_score}* | Son Kapanış: *{latest_close}*

  *Tetiklenme Sebebi:*
  {trigger_reason_lines}

  *Gemini Analizi:*
  {gemini_analysis if gemini_analysis else "_(analiz mevcut değil)_"}
  ```

- [ ] **2.5.2c** `send_signal_notification`:
  ```python
  if not settings.telegram_bot_token or not settings.telegram_chat_id:
      return False
  url = TELEGRAM_API.format(token=settings.telegram_bot_token)
  payload = {
      "chat_id": settings.telegram_chat_id,
      "text": _build_message(result, gemini_analysis),
      "parse_mode": "Markdown",
  }
  with httpx.Client(timeout=10) as client:
      resp = client.post(url, json=payload)
      return resp.status_code == 200
  ```
  - `try/except Exception` ile sarmalayıp hata durumunda `False` dön, loglama yap.

- [ ] **2.5.2d** `SignalResult` dataclass'ına (Adım 1.2.7'de tanımlanacak) `trigger_reasons` alanı eklenebilir
  veya `telegram_service` kendi içinde hesaplar — tercih: **servis kendi içinde hesaplar**,
  `SignalResult`'a dokunulmaz.

---

### ADIM 3 — Yeni Router (`app/routers/signals.py`)

> **Tamamen yeni dosya.** Mevcut routerlara dokunmaz.

#### 3.1 Endpoint Tasarımı

```
GET /portfolios/{portfolio_id}/signals?ticker=AAPL
```

| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `portfolio_id` | int | ✓ | Mevcut portfolio (var mı diye DB'den doğrulanır) |
| `ticker` | str | ✓ | Analiz edilecek hisse (ör. `AAPL`, `THYAO.IS`) |

**Başarı yanıtı (200):**
```json
{
  "ticker": "AAPL",
  "total_score": 3,
  "triggered": true,
  "scores": {
    "rsi": 1,
    "macd": 1,
    "bollinger": 0,
    "stochastic": 1
  },
  "indicators": {
    "rsi_value": 28.4,
    "latest_close": 213.7
  },
  "trigger_reasons": [
    "🟢 RSI → ALIM sinyali (RSI değeri: 28.4)",
    "🟢 MACD → ALIM sinyali (kesişim yukarı)",
    "⚪ Bollinger → Nötr",
    "🟢 Stochastic → ALIM sinyali (%K < %D, 20 seviyesi)"
  ],
  "gemini_analysis": "AAPL hissesi RSI 28.4 ile aşırı satım bölgesine girmiş...",
  "telegram_sent": true
}
```

**Hata yanıtları:**
- `404` — portfolio bulunamadı
- `422` — ticker boş/geçersiz
- `503` — OHLCV verisi çekilemedi

> `telegram_sent: false` bir hata değildir; token eksikse veya Telegram API geçici olarak
> cevap vermiyorsa endpoint yine `200` döner, sadece bu alan `false` olur.

#### 3.2 Router Kodu İskeleti

```python
# app/routers/signals.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Portfolio
from app.services import gemini_analysis_service, signal_service, telegram_service

router = APIRouter()


@router.get("/{portfolio_id}/signals")
def get_signals(
    portfolio_id: int,
    ticker: str = Query(..., min_length=1, max_length=20),
    db: Session = Depends(get_db),
):
    # 1. Portfolio var mı?
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # 2. Sinyalleri hesapla
    try:
        result = signal_service.compute_signal_score(ticker.upper())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # 3. Eşik aşıldıysa Gemini + Telegram'ı sırayla tetikle
    analysis = ""
    telegram_sent = False
    trigger_reasons = telegram_service.build_trigger_reasons(result)  # her zaman hesaplanır

    if result.triggered:
        analysis = gemini_analysis_service.generate_analysis(result)
        telegram_sent = telegram_service.send_signal_notification(result, analysis)

    # 4. Yanıtı döndür
    return {
        "ticker": result.ticker,
        "total_score": result.total_score,
        "triggered": result.triggered,
        "scores": {
            "rsi": result.rsi_score,
            "macd": result.macd_score,
            "bollinger": result.bollinger_score,
            "stochastic": result.stochastic_score,
        },
        "indicators": {
            "rsi_value": result.rsi_value,
            "latest_close": result.latest_close,
        },
        "trigger_reasons": trigger_reasons,
        "gemini_analysis": analysis,
        "telegram_sent": telegram_sent,
    }
```

> `build_trigger_reasons` public fonksiyon olarak `telegram_service`'den dışarı açılır;
> böylece router hem yanıtta kullanır hem de Telegram servisine iletir.

---

### ADIM 4 — `app/main.py` Minimal Güncelleme

> Sadece 2 satır eklenir; başka hiçbir şey değiştirilmez.

- [ ] **4.1** Import ekle:
  ```python
  from app.routers import signals
  ```
- [ ] **4.2** Router'ı bağla:
  ```python
  app.include_router(signals.router, prefix="/portfolios", tags=["signals"])
  ```

---

### ADIM 5 — Birim Testler

> Mevcut testlere dokunulmaz; yeni dosyalar eklenir.

#### `tests/unit/test_signal_service.py`

- [ ] **5.1** `fetch_ohlcv` — boş DataFrame için `ValueError` testi (yfinance mock ile)
- [ ] **5.2** `_score_rsi` testleri:
  - RSI = 28 → +1
  - RSI = 70 → -1
  - RSI = 50 → 0
  - RSI = NaN → 0
- [ ] **5.3** `_score_macd` testleri:
  - Yukarı kesişim → +1
  - Aşağı kesişim → -1
  - Kesişim yok → 0
- [ ] **5.4** `_score_bollinger` testleri:
  - Alt banda dokunuyor → +1
  - Üst banda dokunuyor → -1
  - Ortada → 0
- [ ] **5.5** `_score_stochastic` testleri:
  - Aşağıdan yukarı kesişim (k<20) → +1
  - Yukarıdan aşağı kesişim (k>80) → -1
  - Nötr → 0
- [ ] **5.6** `compute_signal_score` entegrasyon testi (yfinance mock edilir):
  - `triggered=True` senaryosu
  - `triggered=False` senaryosu

#### `tests/unit/test_telegram_service.py`

- [ ] **5.7** `build_trigger_reasons` testleri:
  - Tüm skor `+1` → 4 satır, hepsi `🟢`
  - Tüm skor `-1` → 4 satır, hepsi `🔴`
  - Karışık skorlar → doğru emoji ve detay metni
  - `rsi_value=None` → NaN yerine `"N/A"` gösterir
- [ ] **5.8** `_build_message` testi:
  - Toplam skor > 0 → başlıkta `🟢 ALIM`
  - Toplam skor < 0 → başlıkta `🔴 SATIM`
  - `gemini_analysis=""` → mesajda `_(analiz mevcut değil)_` yer alır
- [ ] **5.9** `send_signal_notification` testleri:
  - `telegram_bot_token=None` → `False` dön, HTTP çağrısı yapma
  - `telegram_chat_id=None` → `False` dön, HTTP çağrısı yapma
  - HTTP 200 → `True` dön (`httpx` mock edilir)
  - HTTP 400 → `False` dön
  - `httpx.TimeoutException` → `False` dön, exception yukarı taşımaz

---

### ADIM 6 — Router Testi (`tests/integration/test_signals_endpoint.py`)

> Mevcut integration testlerine dokunulmaz.

- [ ] **6.1** `GET /portfolios/1/signals?ticker=TEST` — portfolio yok → 404
- [ ] **6.2** `GET /portfolios/{id}/signals?ticker=AAPL` — başarılı, `triggered=True`:
  - yanıtta `trigger_reasons` listesi dolu
  - `gemini_analysis` boş değil
  - `telegram_sent=True` (yfinance + Gemini + httpx mock)
- [ ] **6.3** `GET /portfolios/{id}/signals?ticker=AAPL` — `triggered=False`:
  - `gemini_analysis=""`, `telegram_sent=False`, `trigger_reasons` yine dolu
- [ ] **6.4** `GET /portfolios/{id}/signals` — ticker eksik → 422
- [ ] **6.5** Telegram token eksikse `telegram_sent=False` ama endpoint `200` döner

---

### ADIM 7 — Doğrulama

- [ ] **7.1** Uygulamayı başlat: `uvicorn app.main:app --reload`
- [ ] **7.2** `/docs` üzerinden Swagger'da `signals` tag'inin göründüğünü doğrula
- [ ] **7.3** Manuel çağrı: `GET /portfolios/1/signals?ticker=AAPL`
- [ ] **7.4** `SIGNAL_SCORE_THRESHOLD=0` yapıp Gemini yanıtı ve Telegram mesajı geldiğini doğrula
- [ ] **7.5** Telegram mesajında tetiklenme sebebi (🟢/🔴/⚪ satırları) ve Gemini analizi görünüyor mu?
- [ ] **7.6** Mevcut testlerin kırılmadığını doğrula: `pytest tests/unit/ tests/integration/ -v`

---

## Yeni / Değişen Dosyalar Özeti

| Dosya | Durum | Notlar |
|-------|-------|--------|
| `app/services/signal_service.py` | **YENİ** | İzole sinyal hesaplama |
| `app/services/gemini_analysis_service.py` | **YENİ** | İzole Gemini çağrısı |
| `app/services/telegram_service.py` | **YENİ** | İzole Telegram bildirimi |
| `app/routers/signals.py` | **YENİ** | İzole endpoint |
| `tests/unit/test_signal_service.py` | **YENİ** | Sinyal birim testleri |
| `tests/unit/test_telegram_service.py` | **YENİ** | Telegram birim testleri |
| `tests/integration/test_signals_endpoint.py` | **YENİ** | Router testleri |
| `pyproject.toml` | **MİNİMAL GÜNCELLEME** | 4 paket eklenir |
| `app/config.py` | **MİNİMAL GÜNCELLEME** | 4 alan eklenir |
| `app/main.py` | **MİNİMAL GÜNCELLEME** | 2 satır eklenir |
| `.env.example` | **MİNİMAL GÜNCELLEME** | 4 satır eklenir |

**Dokunulmayan dosyalar (tamamı):**
`app/models/`, `app/schemas/`, `app/database.py`,
`app/routers/portfolios.py`, `app/routers/trades.py`,
`app/routers/export.py`, `app/routers/health.py`,
`app/services/portfolio_service.py`, `app/services/price_service.py`,
`app/services/s3_service.py`, tüm mevcut testler.

---

## Tam Sinyal Akışı

```
İstemci
  │
  │  GET /portfolios/{id}/signals?ticker=AAPL
  ▼
signals.py (router)
  │
  ├── 1. DB: Portfolio var mı? (404 yoksa)
  │
  ├── 2. signal_service.compute_signal_score("AAPL")
  │         │
  │         ├── yfinance.download()  →  OHLCV DataFrame (90 gün)
  │         ├── pandas-ta  →  RSI + MACD + BB + STOCH sütunları
  │         ├── _score_rsi()         →  +1 / 0 / -1
  │         ├── _score_macd()        →  +1 / 0 / -1
  │         ├── _score_bollinger()   →  +1 / 0 / -1
  │         ├── _score_stochastic()  →  +1 / 0 / -1
  │         └── SignalResult(total_score=3, triggered=True, ...)
  │
  ├── 3. telegram_service.build_trigger_reasons(result)   ← her zaman
  │         └── ["🟢 RSI → ALIM ...", "🟢 MACD → ...", ...]
  │
  └── 4. [triggered=True ise]
            │
            ├── gemini_analysis_service.generate_analysis(result)
            │         └── Gemini Flash API  →  "AAPL hissesi..."
            │
            └── telegram_service.send_signal_notification(result, analysis)
                      │
                      ├── _build_message()  →  Markdown metin
                      │       ├── Başlık: "📊 AAPL — 🟢 ALIM SİNYALİ | Skor: 3/4"
                      │       ├── Tetiklenme sebebi (🟢/🔴/⚪ satırları)
                      │       └── Gemini analizi
                      │
                      └── httpx.POST → api.telegram.org  →  telegram_sent: true/false


Yanıt (200):
  {
    ticker, total_score, triggered,
    scores: { rsi, macd, bollinger, stochastic },
    indicators: { rsi_value, latest_close },
    trigger_reasons: [ "🟢 RSI → ...", ... ],   ← tetiklenme sebebi
    gemini_analysis: "...",
    telegram_sent: true
  }
```
