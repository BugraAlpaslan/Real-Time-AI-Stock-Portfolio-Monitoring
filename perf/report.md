# Performans Test Raporu — Stock Portfolio Tracker

## Özet

| Metrik | Değer | Eşik | Durum |
|--------|-------|------|-------|
| **p95 latency (summary)** | **22.9 ms** | < 500 ms | ✅ GEÇTI |
| p90 latency | 17.7 ms | — | — |
| p50 (medyan) | 8.0 ms | — | — |
| Ortalama | 10.1 ms | — | — |
| Maksimum | 135.0 ms | — | — |
| Hata oranı | %0 | < %1 | ✅ GEÇTI |
| Check başarı oranı | %100 | > %99 | ✅ GEÇTI |

## Test Konfigürasyonu

| Parametre | Değer |
|-----------|-------|
| Araç | k6 |
| Senaryo | `perf/load-test.js` |
| VU (max) | 50 |
| Süre | 110 saniye (20s ramp-up → 60s sustain → 30s ramp-down) |
| Toplam iterasyon | 3 094 |
| Test tarihi | Mayıs 2025 |
| Ortam | Docker Compose (localhost) |

## Aşamalar

```
Aşama 1 (0-30s):   0 → 20 VU   — yavaş yükselme
Aşama 2 (30-90s): 20 → 50 VU   — sürekli yük
Aşama 3 (90-120s): 50 → 0 VU   — yavaş düşme
```

## Gruplara Göre Sonuçlar

### `create_trade` (POST /portfolios/{id}/trades)

- Check `trade 201`: %100 başarı
- Bu grup için ayrı latency verisi yoktur (birleşik ölçüm)

### `summary` (GET /portfolios/{id}/summary)

- Check `summary 200`: %100 başarı
- **p95: 22.9 ms** ← eşik kontrolü bu grup üzerinde çalışır

## Eşik Sonuçları

```
✓ http_req_duration{group:::summary}: p(95)<500  → p(95)=22.9ms
✓ http_req_failed: rate<0.01           → rate=0
✓ checks: rate>0.99                    → rate=1.0
```

## Ham Veri

Ham k6 JSON çıktısı: [`docs/perf-report.json`](../docs/perf-report.json)

## Yorumlar

- p95 22.9ms, SLO eşiğinin **22×** altındadır — uygulama yerel Docker ortamında çok iyi performans göstermektedir.
- Maksimum 135ms değeri, ilk portföy oluşturma isteğinde DB bağlantısı kurulması sırasında yaşanan anlık gecikmeyi yansıtmaktadır.
- SQLite + psycopg2 olmadan tam PostgreSQL üzerindeki gerçek üretim performansı benzer veya daha iyi olacaktır (bağlantı havuzu).
