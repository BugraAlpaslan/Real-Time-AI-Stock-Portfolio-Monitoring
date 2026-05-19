"""Optional Locust load test (k6 is primary). Run: locust -f scripts/locustfile.py --host http://localhost:8000"""

from locust import HttpUser, between, task


class PortfolioUser(HttpUser):
    wait_time = between(0.5, 1.5)
    portfolio_id: int | None = None

    def on_start(self) -> None:
        r = self.client.post(
            "/portfolios",
            json={"name": "locust-portfolio", "currency": "USD"},
        )
        if r.ok:
            self.portfolio_id = r.json().get("id")

    @task(3)
    def create_trade(self) -> None:
        if not self.portfolio_id:
            return
        self.client.post(
            f"/portfolios/{self.portfolio_id}/trades",
            json={
                "ticker": "AAPL",
                "trade_type": "BUY",
                "quantity": 1,
                "price": 150,
            },
        )

    @task(1)
    def summary(self) -> None:
        if not self.portfolio_id:
            return
        self.client.get(f"/portfolios/{self.portfolio_id}/summary")
