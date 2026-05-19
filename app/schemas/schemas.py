from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.models.models import TradeType


class PortfolioCreate(BaseModel):
    name: str
    description: str | None = None
    currency: str = "USD"


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    currency: str
    created_at: datetime
    updated_at: datetime


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    quantity: Decimal
    average_cost: Decimal
    realized_pnl: Decimal


class PortfolioWithPositions(PortfolioOut):
    positions: list[PositionOut] = []


class TradeCreate(BaseModel):
    ticker: str
    trade_type: TradeType
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    commission: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = None


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    ticker: str
    trade_type: TradeType
    quantity: Decimal
    price: Decimal
    commission: Decimal
    notes: str | None
    executed_at: datetime


class PositionWithMarket(BaseModel):
    ticker: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal


class SummaryOut(BaseModel):
    total_cost: Decimal
    total_market_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    positions: list[PositionWithMarket]


class ErrorDetail(BaseModel):
    detail: str
    code: str | None = None
