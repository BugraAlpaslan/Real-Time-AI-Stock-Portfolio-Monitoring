# Postman / Newman

## Lokal çalıştırma

```bash
npx newman run postman/stock-portfolio.postman_collection.json \
  -e postman/stock-portfolio.postman_environment.json \
  --reporters cli,htmlextra \
  --reporter-htmlextra-export newman-report.html
```

`baseUrl` varsayılanı `http://localhost:8000`. CI compose içinde `http://app:8000` kullanılabilir.

## Makefile

```bash
make newman
```
