# API Contract — Stock Portfolio Tracker

> **Sahip:** Agent 1 (backend). Diğer agent'lar bu dosyayı referans alır; değişiklik için `integration.md` Work Notes + orkestratör onayı gerekir.

## Hata modeli

Tüm hatalar FastAPI `HTTPException` ile döner. Gövde RFC 7807 benzeri:

```json
{
  "detail": "Human-readable message",
  "code": "MACHINE_CODE"
}
```

| HTTP | `code` | Açıklama |
|------|--------|----------|
| 400 | `INSUFFICIENT_POSITION` | Satışta yeterli pozisyon yok |
| 404 | `NOT_FOUND` | Portföy veya kaynak bulunamadı |
| 422 | — | Pydantic validation (FastAPI default) |

---

## Endpoints

### 1. POST `/portfolios`

**Request body:**

```json
{
  "name": "Growth Fund",
  "description": "optional",
  "currency": "USD"
}
```

| Alan | Tip | Zorunlu | Kurallar |
|------|-----|---------|----------|
| `name` | string | evet | benzersiz |
| `description` | string | hayır | |
| `currency` | string | hayır | default `USD` |

**Response:** `201` — `PortfolioOut`

```json
{
  "id": 1,
  "name": "Growth Fund",
  "description": null,
  "currency": "USD",
  "created_at": "2026-05-19T12:00:00",
  "updated_at": "2026-05-19T12:00:00"
}
```

---

### 2. GET `/portfolios/{id}`

**Response:** `200` — `PortfolioWithPositions` (pozisyonlar dahil)

```json
{
  "id": 1,
  "name": "Growth Fund",
  "description": null,
  "currency": "USD",
  "created_at": "2026-05-19T12:00:00",
  "updated_at": "2026-05-19T12:00:00",
  "positions": [
    {
      "id": 1,
      "ticker": "AAPL",
      "quantity": "10.0000",
      "average_cost": "150.0000",
      "realized_pnl": "0.0000"
    }
  ]
}
```

**Response:** `404` — portföy yok

---

### 3. POST `/portfolios/{id}/trades`

**Request body:**

```json
{
  "ticker": "AAPL",
  "trade_type": "BUY",
  "quantity": "10",
  "price": "150.50",
  "commission": "1.00",
  "notes": "optional"
}
```

| Alan | Tip | Zorunlu | Kurallar |
|------|-----|---------|----------|
| `ticker` | string | evet | |
| `trade_type` | `"BUY"` \| `"SELL"` | evet | |
| `quantity` | decimal | evet | > 0 |
| `price` | decimal | evet | > 0 |
| `commission` | decimal | hayır | >= 0, default 0 |
| `notes` | string | hayır | |

**Response:** `201` — `TradeOut`

**Response:** `400` — `INSUFFICIENT_POSITION`

**Response:** `404` — portföy yok

---

### 4. GET `/portfolios/{id}/trades`

**Query params:** `ticker` (optional), `limit` (optional, default 50)

**Response:** `200` — `list[TradeOut]`

---

### 5. GET `/portfolios/{id}/summary`

**Response:** `200` — `SummaryOut`

```json
{
  "total_cost": "1500.00",
  "total_market_value": "1600.00",
  "realized_pnl": "100.00",
  "unrealized_pnl": "100.00",
  "total_pnl": "200.00",
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": "10.0000",
      "average_cost": "150.0000",
      "current_price": "160.0000",
      "market_value": "1600.0000",
      "cost_basis": "1500.0000",
      "realized_pnl": "0.0000",
      "unrealized_pnl": "100.0000"
    }
  ]
}
```

---

### 6. GET `/health`

**Response:** `200`

```json
{
  "status": "ok",
  "db": "up"
}
```

---

### 7. GET `/metrics`

**Response:** `200` — Prometheus text exposition (`prometheus_fastapi_instrumentator`)

---

## P&L kuralları (servis katmanı)

### BUY

- Pozisyon yoksa oluştur.
- `quantity += q`
- `average_cost = (eski_q * eski_avg + q * price + commission) / yeni_q`

### SELL

- Pozisyonda yeterli adet yoksa → `400 INSUFFICIENT_POSITION`
- `realized_pnl += (price - average_cost) * q - commission`
- `quantity -= q` (sıfır olunca pozisyon silinmez, history için tutulur)

### Unrealized P&L (Phase 1)

- `unrealized_pnl = Σ (current_price - average_cost) * quantity`
- `current_price` = aynı ticker için son trade fiyatı; trade yoksa `average_cost` (unrealized = 0)

### Phase 2

- `current_price` Midas API'den (`MIDAS_BASE_URL`)
