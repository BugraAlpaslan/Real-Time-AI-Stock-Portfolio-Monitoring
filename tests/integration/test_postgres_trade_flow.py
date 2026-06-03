import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import models  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.testcontainers]


@pytest.fixture(scope="module")
def pg_url():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="module")
def pg_client(pg_url):
    engine = create_engine(pg_url)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_postgres_full_buy_sell_flow_realized_pnl(pg_client):
    create = pg_client.post("/portfolios", json={"name": "PG-Flow"})
    pid = create.json()["id"]
    pg_client.post(
        f"/portfolios/{pid}/trades",
        json={"ticker": "AAPL", "trade_type": "BUY", "quantity": "10", "price": "100"},
    )
    pg_client.post(
        f"/portfolios/{pid}/trades",
        json={"ticker": "AAPL", "trade_type": "SELL", "quantity": "5", "price": "120"},
    )
    summary = pg_client.get(f"/portfolios/{pid}/summary")
    assert summary.status_code == 200
    assert float(summary.json()["realized_pnl"]) == 100.0


def test_postgres_summary_endpoint_with_real_pg(pg_client):
    create = pg_client.post("/portfolios", json={"name": "PG-Summary"})
    pid = create.json()["id"]
    response = pg_client.get(f"/portfolios/{pid}/summary")
    assert response.status_code == 200
    assert response.json()["positions"] == []
