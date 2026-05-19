from decimal import Decimal

import pytest

from app.models.models import TradeType
from app.schemas.schemas import PortfolioCreate, TradeCreate
from app.services import portfolio_service


def test_create_portfolio_persists(db_session):
    payload = PortfolioCreate(name="Alpha", currency="TRY")
    portfolio = portfolio_service.create_portfolio(db_session, payload)
    assert portfolio.id is not None
    assert portfolio.name == "Alpha"
    assert portfolio.currency == "TRY"


def test_get_portfolio_not_found_raises(db_session):
    with pytest.raises(LookupError):
        portfolio_service.get_portfolio(db_session, 9999)


def test_buy_creates_position(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="B1"))
    trade = portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.BUY, quantity=Decimal("5"), price=Decimal("100")
        ),
    )
    assert trade.id is not None
    portfolio = portfolio_service.get_portfolio(db_session, p.id)
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].quantity == Decimal("5")


def test_buy_existing_position_updates_average_cost(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="B2"))
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="MSFT", trade_type=TradeType.BUY, quantity=Decimal("10"), price=Decimal("100")
        ),
    )
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="MSFT", trade_type=TradeType.BUY, quantity=Decimal("10"), price=Decimal("120")
        ),
    )
    pos = portfolio_service.get_portfolio(db_session, p.id).positions[0]
    assert pos.quantity == Decimal("20")
    assert pos.average_cost == Decimal("110")


def test_buy_average_cost_includes_commission(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="B3"))
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="GOOG",
            trade_type=TradeType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            commission=Decimal("10"),
        ),
    )
    pos = portfolio_service.get_portfolio(db_session, p.id).positions[0]
    assert pos.average_cost == Decimal("101")


def test_sell_reduces_quantity(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="S1"))
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.BUY, quantity=Decimal("10"), price=Decimal("100")
        ),
    )
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.SELL, quantity=Decimal("3"), price=Decimal("110")
        ),
    )
    pos = portfolio_service.get_portfolio(db_session, p.id).positions[0]
    assert pos.quantity == Decimal("7")


def test_sell_realized_pnl_calculation(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="S2"))
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.BUY, quantity=Decimal("100"), price=Decimal("100")
        ),
    )
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL",
            trade_type=TradeType.SELL,
            quantity=Decimal("50"),
            price=Decimal("120"),
            commission=Decimal("5"),
        ),
    )
    pos = portfolio_service.get_portfolio(db_session, p.id).positions[0]
    assert pos.realized_pnl == Decimal("995")


def test_sell_insufficient_raises_value_error(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="S3"))
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.BUY, quantity=Decimal("5"), price=Decimal("100")
        ),
    )
    with pytest.raises(ValueError, match="INSUFFICIENT_POSITION"):
        portfolio_service.add_trade(
            db_session,
            p.id,
            TradeCreate(
                ticker="AAPL",
                trade_type=TradeType.SELL,
                quantity=Decimal("10"),
                price=Decimal("110"),
            ),
        )


def test_sell_on_missing_position_raises(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="S4"))
    with pytest.raises(ValueError, match="INSUFFICIENT_POSITION"):
        portfolio_service.add_trade(
            db_session,
            p.id,
            TradeCreate(
                ticker="NEW", trade_type=TradeType.SELL, quantity=Decimal("1"), price=Decimal("50")
            ),
        )


def test_list_trades_filtered_by_ticker(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="L1"))
    for ticker in ("A", "B", "A"):
        portfolio_service.add_trade(
            db_session,
            p.id,
            TradeCreate(
                ticker=ticker, trade_type=TradeType.BUY, quantity=Decimal("1"), price=Decimal("10")
            ),
        )
    trades = portfolio_service.list_trades(db_session, p.id, ticker="A")
    assert len(trades) == 2
    assert all(t.ticker == "A" for t in trades)


def test_list_trades_limit_respected(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="L2"))
    for _ in range(5):
        portfolio_service.add_trade(
            db_session,
            p.id,
            TradeCreate(
                ticker="X", trade_type=TradeType.BUY, quantity=Decimal("1"), price=Decimal("1")
            ),
        )
    trades = portfolio_service.list_trades(db_session, p.id, limit=3)
    assert len(trades) == 3


def test_summary_no_positions_returns_zero(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="Sum1"))
    summary = portfolio_service.compute_summary(db_session, p.id)
    assert summary.total_cost == Decimal("0")
    assert summary.total_pnl == Decimal("0")
    assert summary.positions == []


def test_summary_unrealized_with_last_trade_price(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="Sum2"))
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.BUY, quantity=Decimal("10"), price=Decimal("100")
        ),
    )
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.BUY, quantity=Decimal("5"), price=Decimal("130")
        ),
    )
    # avg=(10*100+5*130)/15=110; last price=130 → unrealized=(130-110)*15=300
    summary = portfolio_service.compute_summary(db_session, p.id)
    assert summary.unrealized_pnl == Decimal("300")


def test_summary_total_pnl_sums_realized_and_unrealized(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="Sum3"))
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.BUY, quantity=Decimal("10"), price=Decimal("100")
        ),
    )
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.SELL, quantity=Decimal("5"), price=Decimal("120")
        ),
    )
    summary = portfolio_service.compute_summary(db_session, p.id)
    assert summary.total_pnl == summary.realized_pnl + summary.unrealized_pnl


def test_summary_with_custom_price_provider(db_session):
    p = portfolio_service.create_portfolio(db_session, PortfolioCreate(name="Sum4"))
    portfolio_service.add_trade(
        db_session,
        p.id,
        TradeCreate(
            ticker="AAPL", trade_type=TradeType.BUY, quantity=Decimal("2"), price=Decimal("100")
        ),
    )
    summary = portfolio_service.compute_summary(
        db_session, p.id, price_provider=lambda _ticker: Decimal("999")
    )
    assert summary.positions[0].current_price == Decimal("999")
    assert summary.unrealized_pnl == Decimal("1798")
