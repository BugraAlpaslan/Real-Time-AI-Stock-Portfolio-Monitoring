from collections.abc import Callable
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.models import Portfolio, Position, Trade, TradeType
from app.schemas.schemas import (
    PortfolioCreate,
    PortfolioWithPositions,
    PositionWithMarket,
    SummaryOut,
    TradeCreate,
)


def _to_decimal(value: Decimal | float | int) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def create_portfolio(db: Session, payload: PortfolioCreate) -> Portfolio:
    portfolio = Portfolio(
        name=payload.name,
        description=payload.description,
        currency=payload.currency,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def get_portfolio(db: Session, portfolio_id: int) -> Portfolio:
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise LookupError(f"Portfolio {portfolio_id} not found")
    return portfolio


def _get_or_create_position(db: Session, portfolio_id: int, ticker: str) -> Position:
    stmt = select(Position).where(
        Position.portfolio_id == portfolio_id,
        Position.ticker == ticker,
    )
    position = db.execute(stmt).scalar_one_or_none()
    if position is None:
        position = Position(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=Decimal("0"),
            average_cost=Decimal("0"),
            realized_pnl=Decimal("0"),
        )
        db.add(position)
        db.flush()
    return position


def _last_trade_price(db: Session, portfolio_id: int, ticker: str) -> Decimal | None:
    stmt = (
        select(Trade)
        .where(Trade.portfolio_id == portfolio_id, Trade.ticker == ticker)
        .order_by(desc(Trade.executed_at), desc(Trade.id))
        .limit(1)
    )
    trade = db.execute(stmt).scalar_one_or_none()
    if trade is None:
        return None
    return _to_decimal(trade.price)


def add_trade(db: Session, portfolio_id: int, payload: TradeCreate) -> Trade:
    portfolio = (
        db.query(Portfolio).filter(Portfolio.id == portfolio_id).with_for_update().one_or_none()
    )
    if portfolio is None:
        raise LookupError(f"Portfolio {portfolio_id} not found")

    position = _get_or_create_position(db, portfolio_id, payload.ticker)
    qty = _to_decimal(payload.quantity)
    price = _to_decimal(payload.price)
    commission = _to_decimal(payload.commission)

    if payload.trade_type == TradeType.BUY:
        old_qty = _to_decimal(position.quantity)
        old_avg = _to_decimal(position.average_cost)
        new_qty = old_qty + qty
        if new_qty > 0:
            position.average_cost = (old_qty * old_avg + qty * price + commission) / new_qty
        position.quantity = new_qty
    else:
        current_qty = _to_decimal(position.quantity)
        if current_qty < qty:
            raise ValueError("INSUFFICIENT_POSITION")
        avg_cost = _to_decimal(position.average_cost)
        position.realized_pnl = (
            _to_decimal(position.realized_pnl) + (price - avg_cost) * qty - commission
        )
        position.quantity = current_qty - qty

    trade = Trade(
        portfolio_id=portfolio_id,
        ticker=payload.ticker,
        trade_type=payload.trade_type,
        quantity=qty,
        price=price,
        commission=commission,
        notes=payload.notes,
    )
    db.add(trade)
    db.flush()
    db.refresh(trade)
    db.commit()
    return trade


def list_trades(
    db: Session,
    portfolio_id: int,
    ticker: str | None = None,
    limit: int = 50,
) -> list[Trade]:
    get_portfolio(db, portfolio_id)
    stmt = select(Trade).where(Trade.portfolio_id == portfolio_id)
    if ticker is not None:
        stmt = stmt.where(Trade.ticker == ticker)
    stmt = stmt.order_by(desc(Trade.executed_at), desc(Trade.id)).limit(limit)
    return list(db.execute(stmt).scalars().all())


def compute_summary(
    db: Session,
    portfolio_id: int,
    price_provider: Callable[[str], Decimal | None] | None = None,
) -> SummaryOut:
    portfolio = get_portfolio(db, portfolio_id)
    positions = list(portfolio.positions)

    total_cost = Decimal("0")
    total_market_value = Decimal("0")
    realized_total = Decimal("0")
    unrealized_total = Decimal("0")
    position_rows: list[PositionWithMarket] = []

    for pos in positions:
        qty = _to_decimal(pos.quantity)
        if qty <= 0:
            continue

        avg_cost = _to_decimal(pos.average_cost)
        realized = _to_decimal(pos.realized_pnl)

        if price_provider is not None:
            current_price = price_provider(pos.ticker)
        else:
            current_price = _last_trade_price(db, portfolio_id, pos.ticker)

        if current_price is None:
            current_price = avg_cost

        cost_basis = qty * avg_cost
        market_value = qty * current_price
        unrealized = (current_price - avg_cost) * qty

        total_cost += cost_basis
        total_market_value += market_value
        realized_total += realized
        unrealized_total += unrealized

        position_rows.append(
            PositionWithMarket(
                ticker=pos.ticker,
                quantity=qty,
                average_cost=avg_cost,
                current_price=current_price,
                market_value=market_value,
                cost_basis=cost_basis,
                realized_pnl=realized,
                unrealized_pnl=unrealized,
            )
        )

    return SummaryOut(
        total_cost=total_cost,
        total_market_value=total_market_value,
        realized_pnl=realized_total,
        unrealized_pnl=unrealized_total,
        total_pnl=realized_total + unrealized_total,
        positions=position_rows,
    )


def get_portfolio_with_positions(db: Session, portfolio_id: int) -> PortfolioWithPositions:
    portfolio = get_portfolio(db, portfolio_id)
    return PortfolioWithPositions.model_validate(portfolio)
