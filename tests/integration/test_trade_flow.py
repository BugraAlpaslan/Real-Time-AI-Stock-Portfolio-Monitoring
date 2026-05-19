import pytest

pytestmark = pytest.mark.integration


def test_buy_then_sell_realized_pnl_visible_in_summary(client):
    create = client.post("/portfolios", json={"name": "TradeFlow"})
    pid = create.json()["id"]
    client.post(
        f"/portfolios/{pid}/trades",
        json={"ticker": "AAPL", "trade_type": "BUY", "quantity": "10", "price": "100"},
    )
    client.post(
        f"/portfolios/{pid}/trades",
        json={"ticker": "AAPL", "trade_type": "SELL", "quantity": "5", "price": "120"},
    )
    summary = client.get(f"/portfolios/{pid}/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert float(data["realized_pnl"]) == 100.0


def test_sell_insufficient_returns_400_with_code(client):
    create = client.post("/portfolios", json={"name": "Insufficient"})
    pid = create.json()["id"]
    response = client.post(
        f"/portfolios/{pid}/trades",
        json={"ticker": "AAPL", "trade_type": "SELL", "quantity": "1", "price": "100"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["code"] == "INSUFFICIENT_POSITION"


def test_list_trades_after_multiple_buys(client):
    create = client.post("/portfolios", json={"name": "ListTrades"})
    pid = create.json()["id"]
    for i in range(3):
        client.post(
            f"/portfolios/{pid}/trades",
            json={
                "ticker": "MSFT",
                "trade_type": "BUY",
                "quantity": "1",
                "price": str(100 + i),
            },
        )
    response = client.get(f"/portfolios/{pid}/trades?ticker=MSFT")
    assert response.status_code == 200
    assert len(response.json()) == 3
