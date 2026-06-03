import pytest

pytestmark = pytest.mark.integration


def test_summary_aggregates_multi_ticker_pnl(client):
    create = client.post("/portfolios", json={"name": "MultiTicker"})
    pid = create.json()["id"]
    client.post(
        f"/portfolios/{pid}/trades",
        json={"ticker": "AAPL", "trade_type": "BUY", "quantity": "10", "price": "100"},
    )
    client.post(
        f"/portfolios/{pid}/trades",
        json={"ticker": "GOOG", "trade_type": "BUY", "quantity": "5", "price": "200"},
    )
    summary = client.get(f"/portfolios/{pid}/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert len(data["positions"]) == 2
    assert float(data["total_cost"]) > 0


def test_summary_zero_for_empty_portfolio(client):
    create = client.post("/portfolios", json={"name": "Empty"})
    pid = create.json()["id"]
    summary = client.get(f"/portfolios/{pid}/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert float(data["total_pnl"]) == 0.0
    assert data["positions"] == []
