# İş Paylaşımı — Stock Portfolio Tracker

MTH2526-B25 · Bulut Mimarilerinde Test Mühendisliği · Marmara Üniversitesi · 2024-25 Bahar

## Grup Üyeleri

| İsim | Öğrenci No | GitHub |
|------|-----------|--------|
| Mehmet İhsan Ekinci | 210444064 | mihsanekinci |
| Buğra Alpaslan | 210444020 | BugraAlpaslan |

## Modül Sorumluluğu

| Modül | Birincil Sorumlu | Yardımcı |
|-------|-----------------|---------|
| FastAPI REST endpoint'leri | Mehmet İhsan Ekinci | Buğra Alpaslan |
| SQLAlchemy modelleri & şemalar | Mehmet İhsan Ekinci | — |
| P&L hesaplama servisi | Mehmet İhsan Ekinci | — |
| Fiyat servisi (MIDAS + Yahoo) | Mehmet İhsan Ekinci | — |
| Unit & integration testler (pytest) | Mehmet İhsan Ekinci | Buğra Alpaslan |
| Testcontainers PostgreSQL testleri | Mehmet İhsan Ekinci | — |
| Factory Boy test fabrikaları | Mehmet İhsan Ekinci | — |
| Multi-stage Dockerfile | Buğra Alpaslan | Mehmet İhsan Ekinci |
| docker-compose.yml (5 servis) | Buğra Alpaslan | — |
| LocalStack S3 entegrasyonu | Buğra Alpaslan | Mehmet İhsan Ekinci |
| Kubernetes manifestleri (k8s/) | Buğra Alpaslan | — |
| GitHub Actions CI pipeline (5 job) | Buğra Alpaslan | Mehmet İhsan Ekinci |
| Postman koleksiyonu + Newman | Buğra Alpaslan | — |
| Statik Web UI (HTML/CSS/JS) | Buğra Alpaslan | Mehmet İhsan Ekinci |
| Playwright E2E testler (6 senaryo) | Buğra Alpaslan | — |
| Prometheus + Grafana izleme | Buğra Alpaslan | Mehmet İhsan Ekinci |
| k6 performans testleri | Buğra Alpaslan | — |
| README + mimari doküman | Buğra Alpaslan | Mehmet İhsan Ekinci |
| Final rapor | Mehmet İhsan Ekinci | Buğra Alpaslan |

## Sprint Takvimi

| Sprint | Tarih Aralığı | Teslim |
|--------|--------------|--------|
| Sprint 1 | Nisan 2025 | FastAPI app, temel testler, PostgreSQL |
| Sprint 2 | Mayıs 2025 | Docker, K8s, CI/CD, LocalStack, UI |
| Sprint 3 | Haziran 2025 | E2E, Monitoring, Performans, Dokümantasyon |

## Sunum Planı (20 dakika)

| Zaman | Konu | Sorumlu |
|-------|------|---------|
| 0-7 dk | Problem tanımı · Mimari · Test stratejisi | Mehmet İhsan Ekinci |
| 7-14 dk | Canlı demo (docker compose up → portföy oluştur → işlem ekle → özet) | Buğra Alpaslan |
| 14-17 dk | Sayılar: coverage, p95 latency, CI yeşil ekran | Mehmet İhsan Ekinci |
| 17-20 dk | Q&A | İkisi birlikte |

## Katkı Özeti

- **Toplam commit:** ≥ 30 (ikisi de aktif katkıda bulundu)
- **Test coverage:** %84 (eşik: %70)
- **CI geçen pipeline:** 5 job, tamamı yeşil
- **Doküman sayısı:** README, architecture.md, api-contract.md, final-report.md, demo-script.md, integration.md, work-distribution.md
