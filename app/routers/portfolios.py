from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import PortfolioCreate, PortfolioOut, PortfolioWithPositions, SummaryOut
from app.services import portfolio_service

router = APIRouter()


@router.post("", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
def create_portfolio(payload: PortfolioCreate, db: Session = Depends(get_db)) -> PortfolioOut:
    portfolio = portfolio_service.create_portfolio(db, payload)
    return PortfolioOut.model_validate(portfolio)


@router.get("/{portfolio_id}", response_model=PortfolioWithPositions)
def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> PortfolioWithPositions:
    try:
        return portfolio_service.get_portfolio_with_positions(db, portfolio_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
            headers={"X-Error-Code": "NOT_FOUND"},
        ) from exc


@router.get("/{portfolio_id}/summary", response_model=SummaryOut)
def get_summary(portfolio_id: int, db: Session = Depends(get_db)) -> SummaryOut:
    try:
        return portfolio_service.compute_summary(db, portfolio_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
            headers={"X-Error-Code": "NOT_FOUND"},
        ) from exc
