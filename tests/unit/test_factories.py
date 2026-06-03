from decimal import Decimal

from app.models.models import TradeType
from tests.factories import (
    BuyTradeFactory,
    PortfolioFactory,
    PositionFactory,
    TradeFactory,
    with_trades,
)


def test_portfolio_factory_single_instance(db_session):
    p = PortfolioFactory()
    assert p.id is not None
    assert p.name.startswith("Portfolio-")


def test_buy_trade_factory_trade_type(db_session):
    t = BuyTradeFactory()
    assert t.trade_type == TradeType.BUY


def test_create_batch_unique_tickers(db_session):
    portfolio = PortfolioFactory()
    trades = TradeFactory.create_batch(10, portfolio=portfolio)
    tickers = {t.ticker for t in trades}
    assert len(tickers) == 10


def test_position_factory_referential_integrity(db_session):
    pos = PositionFactory()
    assert pos.portfolio_id == pos.portfolio.id
    assert pos.quantity == Decimal("10")


def test_with_trades_helper(db_session):
    portfolio = with_trades(5)
    assert len(portfolio.trades) == 5
