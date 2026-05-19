from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import TradeCreate, TradeOut
from app.services import portfolio_service

router = APIRouter()


@router.post("/{portfolio_id}/trades", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
def add_trade(
    portfolio_id: int,
    payload: TradeCreate,
    db: Session = Depends(get_db),
) -> TradeOut:
    try:
        trade = portfolio_service.add_trade(db, portfolio_id, payload)
        return TradeOut.model_validate(trade)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        if str(exc) == "INSUFFICIENT_POSITION":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"detail": str(exc), "code": "INSUFFICIENT_POSITION"},
            ) from exc
        raise


@router.get("/{portfolio_id}/trades", response_model=list[TradeOut])
def list_trades(
    portfolio_id: int,
    ticker: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[TradeOut]:
    try:
        trades = portfolio_service.list_trades(db, portfolio_id, ticker=ticker, limit=limit)
        return [TradeOut.model_validate(t) for t in trades]
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
