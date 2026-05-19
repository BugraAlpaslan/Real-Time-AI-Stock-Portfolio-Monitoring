from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.models import Portfolio, Position, Trade, TradeType
from tests.factories import PortfolioFactory, PositionFactory


def test_unique_constraint_portfolio_ticker(db_session):
    portfolio = PortfolioFactory()
    PositionFactory(portfolio=portfolio, ticker="AAPL")
    with pytest.raises(IntegrityError):
        PositionFactory(portfolio=portfolio, ticker="AAPL")
        db_session.commit()


def test_cascade_delete_removes_trades_and_positions(db_session):
    portfolio = PortfolioFactory()
    position = PositionFactory(portfolio=portfolio, ticker="MSFT")
    trade = Trade(
        portfolio_id=portfolio.id,
        ticker="MSFT",
        trade_type=TradeType.BUY,
        quantity=Decimal("1"),
        price=Decimal("10"),
        commission=Decimal("0"),
    )
    db_session.add(trade)
    db_session.commit()

    db_session.delete(portfolio)
    db_session.commit()

    assert db_session.get(Portfolio, portfolio.id) is None
    assert db_session.get(Position, position.id) is None
    assert db_session.get(Trade, trade.id) is None


def test_trade_type_enum_string_serialization():
    assert TradeType.BUY.value == "BUY"
    assert TradeType.SELL.value == "SELL"
    assert str(TradeType.BUY) == "TradeType.BUY"
