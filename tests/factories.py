from decimal import Decimal

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.models import Portfolio, Position, Trade, TradeType


class PortfolioFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Portfolio
        sqlalchemy_session_persistence = "commit"

    name = factory.Sequence(lambda n: f"Portfolio-{n}")
    description = factory.Faker("sentence")
    currency = "USD"


class TradeFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Trade
        sqlalchemy_session_persistence = "commit"

    portfolio = factory.SubFactory(PortfolioFactory)
    portfolio_id = factory.SelfAttribute("portfolio.id")
    ticker = factory.Sequence(lambda n: f"TKR{n:04d}")
    trade_type = TradeType.BUY
    quantity = Decimal("10")
    price = Decimal("100")
    commission = Decimal("0")
    notes = None


class BuyTradeFactory(TradeFactory):
    trade_type = TradeType.BUY


class SellTradeFactory(TradeFactory):
    trade_type = TradeType.SELL


class PositionFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Position
        sqlalchemy_session_persistence = "commit"

    portfolio = factory.SubFactory(PortfolioFactory)
    portfolio_id = factory.SelfAttribute("portfolio.id")
    ticker = factory.Sequence(lambda n: f"POS{n:04d}")
    quantity = Decimal("10")
    average_cost = Decimal("100")
    realized_pnl = Decimal("0")


def with_trades(n: int = 5) -> Portfolio:
    portfolio = PortfolioFactory()
    TradeFactory.create_batch(n, portfolio=portfolio)
    return portfolio
