from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.models import TradeType
from app.schemas.schemas import PortfolioCreate, TradeCreate


def test_negative_quantity_rejected():
    with pytest.raises(ValidationError):
        TradeCreate(
            ticker="A",
            trade_type=TradeType.BUY,
            quantity=Decimal("-1"),
            price=Decimal("10"),
        )


def test_negative_price_rejected():
    with pytest.raises(ValidationError):
        TradeCreate(
            ticker="A",
            trade_type=TradeType.BUY,
            quantity=Decimal("1"),
            price=Decimal("-5"),
        )


def test_invalid_trade_type_rejected():
    with pytest.raises(ValidationError):
        TradeCreate.model_validate(
            {
                "ticker": "A",
                "trade_type": "HOLD",
                "quantity": "1",
                "price": "10",
            }
        )


def test_default_currency():
    p = PortfolioCreate(name="Test")
    assert p.currency == "USD"


def test_missing_name_rejected():
    with pytest.raises(ValidationError):
        PortfolioCreate.model_validate({"currency": "USD"})


def test_negative_commission_rejected():
    with pytest.raises(ValidationError):
        TradeCreate(
            ticker="A",
            trade_type=TradeType.BUY,
            quantity=Decimal("1"),
            price=Decimal("10"),
            commission=Decimal("-1"),
        )
