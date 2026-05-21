import http from "k6/http";
import { check, sleep, group } from "k6";

export const options = {
  stages: [
    { duration: "30s", target: 20 },
    { duration: "1m", target: 50 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    "http_req_duration{group:::summary}": ["p(95)<500"],
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:8000";

export function setup() {
  const r = http.post(
    `${BASE}/portfolios`,
    JSON.stringify({ name: `perf-${Date.now()}`, currency: "USD" }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(r, { "portfolio 201": (res) => res.status === 201 });
  return { portfolioId: r.json("id") };
}

export default function (data) {
  group("create_trade", () => {
    const r = http.post(
      `${BASE}/portfolios/${data.portfolioId}/trades`,
      JSON.stringify({
        ticker: "AAPL",
        trade_type: "BUY",
        quantity: 1,
        price: 150,
      }),
      { headers: { "Content-Type": "application/json" } },
    );
    check(r, { "trade 201": (res) => res.status === 201 });
  });

  group("summary", () => {
    const r = http.get(`${BASE}/portfolios/${data.portfolioId}/summary`);
    check(r, { "summary 200": (res) => res.status === 200 });
  });

  sleep(1);
}

export function handleSummary(data) {
  return {
    "/docs/perf-report.json": JSON.stringify(data, null, 2),
    stdout: JSON.stringify(data, null, 2),
  };
}
