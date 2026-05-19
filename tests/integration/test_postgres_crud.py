import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.models import Portfolio, Position
from app.schemas.schemas import PortfolioCreate, TradeCreate
from app.models.models import TradeType
from app.services import portfolio_service

pytestmark = [pytest.mark.integration, pytest.mark.testcontainers]


@pytest.fixture(scope="module")
def pg_url():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="module")
def pg_engine(pg_url):
    engine = create_engine(pg_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def pg_session(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def test_postgres_create_and_query_portfolio(pg_session):
    portfolio = portfolio_service.create_portfolio(
        pg_session, PortfolioCreate(name="PG-Unique-1", currency="USD")
    )
    fetched = portfolio_service.get_portfolio(pg_session, portfolio.id)
    assert fetched.name == "PG-Unique-1"

    duplicate = Portfolio(name="PG-Unique-1", currency="EUR")
    pg_session.add(duplicate)
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_concurrent_trades_consistency(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autocommit=False, autoflush=False)
    session1 = SessionLocal()
    session2 = SessionLocal()

    portfolio = portfolio_service.create_portfolio(
        session1, PortfolioCreate(name="PG-Concurrent", currency="USD")
    )
    session1.commit()

    portfolio_service.add_trade(
        session1,
        portfolio.id,
        TradeCreate(ticker="AAPL", trade_type=TradeType.BUY, quantity=10, price=100),
    )
    portfolio_service.add_trade(
        session2,
        portfolio.id,
        TradeCreate(ticker="AAPL", trade_type=TradeType.BUY, quantity=5, price=110),
    )

    pos = session2.query(Position).filter_by(portfolio_id=portfolio.id, ticker="AAPL").one()
    assert float(pos.quantity) == 15.0

    session1.close()
    session2.close()
