from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Portfolio, Trade
from app.services.s3_service import S3Service, get_s3_service

router = APIRouter()


class ExportResponse(BaseModel):
    s3_uri: str
    size_bytes: int
    trade_count: int


def _serialize_trades(trades: list[Trade]) -> list[dict]:
    return [
        {
            "id": trade.id,
            "portfolio_id": trade.portfolio_id,
            "ticker": trade.ticker,
            "trade_type": trade.trade_type.value
            if hasattr(trade.trade_type, "value")
            else str(trade.trade_type),
            "quantity": float(trade.quantity),
            "price": float(trade.price),
            "commission": float(trade.commission) if trade.commission is not None else 0.0,
            "notes": trade.notes,
            "executed_at": trade.executed_at.isoformat() if trade.executed_at else None,
        }
        for trade in trades
    ]


@router.post("/{portfolio_id}/export", response_model=ExportResponse)
def export_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    s3: S3Service = Depends(get_s3_service),
) -> ExportResponse:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    trades = (
        db.query(Trade)
        .filter(Trade.portfolio_id == portfolio_id)
        .order_by(Trade.executed_at.asc(), Trade.id.asc())
        .all()
    )
    payload = {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        "currency": portfolio.currency,
        "exported_at": datetime.now(UTC).isoformat(),
        "trades": _serialize_trades(trades),
    }
    body = json.dumps(payload, ensure_ascii=False)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    key = f"portfolio-{portfolio_id}/{timestamp}.json"
    s3_uri = s3.put_object(key, body)
    encoded = body.encode("utf-8")
    return ExportResponse(
        s3_uri=s3_uri,
        size_bytes=len(encoded),
        trade_count=len(trades),
    )
