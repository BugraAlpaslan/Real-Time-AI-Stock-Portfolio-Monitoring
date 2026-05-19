import pytest

pytestmark = pytest.mark.integration


def test_create_portfolio_201(client):
    response = client.post(
        "/portfolios",
        json={"name": "Integration Fund", "currency": "USD"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Integration Fund"
    assert "id" in data


def test_get_portfolio_with_positions(client):
    create = client.post("/portfolios", json={"name": "WithPos"})
    portfolio_id = create.json()["id"]
    client.post(
        f"/portfolios/{portfolio_id}/trades",
        json={
            "ticker": "AAPL",
            "trade_type": "BUY",
            "quantity": "10",
            "price": "150",
        },
    )
    response = client.get(f"/portfolios/{portfolio_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["positions"]) == 1
    assert data["positions"][0]["ticker"] == "AAPL"


def test_get_portfolio_404(client):
    response = client.get("/portfolios/99999")
    assert response.status_code == 404


def test_health_returns_db_up(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "up"}
