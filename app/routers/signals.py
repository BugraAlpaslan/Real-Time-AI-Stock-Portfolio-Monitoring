from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Portfolio, Position
from app.models.models import SignalAnalysis
from app.services import gemini_analysis_service, signal_service, telegram_service

router = APIRouter()


@router.get("/{portfolio_id}/signals")
def get_signals(
    portfolio_id: int,
    ticker: str = Query(
        ..., min_length=1, max_length=20, description="Hisse kodu (ör. AAPL, THYAO.IS)"
    ),
    db: Session = Depends(get_db),
):
    """
    Verilen hisse için 4 teknik indikatör (RSI, MACD, Bollinger, Stochastic) hesaplar,
    sinyal skoru eşiği aşılırsa Gemini analizi üretir ve Telegram bildirimi gönderir.
    Portföyde bu hisse varsa maliyet/adet bilgisini de Gemini'ye iletir.
    """
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    try:
        result = signal_service.compute_signal_score(ticker.upper())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Portföydeki pozisyonu bul (yoksa None)
    position = (
        db.query(Position)
        .filter(Position.portfolio_id == portfolio_id, Position.ticker == ticker.upper())
        .first()
    )
    position_data = None
    if position and float(position.quantity) > 0:
        avg_cost = float(position.average_cost)
        quantity = float(position.quantity)
        current = result.latest_close or 0.0
        unrealized_pnl = (current - avg_cost) * quantity
        pnl_pct = ((current - avg_cost) / avg_cost * 100) if avg_cost else 0.0
        position_data = {
            "quantity": quantity,
            "average_cost": avg_cost,
            "total_cost": avg_cost * quantity,
            "current_value": current * quantity,
            "unrealized_pnl": unrealized_pnl,
            "pnl_pct": pnl_pct,
            "realized_pnl": float(position.realized_pnl),
        }

    trigger_reasons = telegram_service.build_trigger_reasons(result)

    analysis = ""
    telegram_sent = False
    if result.triggered:
        analysis = gemini_analysis_service.generate_analysis(result, position_data=position_data)
        telegram_sent = telegram_service.send_signal_notification(
            result, analysis, chat_id=portfolio.telegram_chat_id
        )

    # Analizi DB'ye kaydet
    record = SignalAnalysis(
        portfolio_id=portfolio_id,
        ticker=result.ticker,
        total_score=result.total_score,
        rsi_score=result.rsi_score,
        macd_score=result.macd_score,
        bollinger_score=result.bollinger_score,
        stochastic_score=result.stochastic_score,
        rsi_value=result.rsi_value,
        latest_close=result.latest_close,
        triggered=result.triggered,
        gemini_analysis=analysis or None,
        telegram_sent=telegram_sent,
    )
    db.add(record)
    db.commit()

    return {
        "id": record.id,
        "ticker": result.ticker,
        "total_score": result.total_score,
        "triggered": result.triggered,
        "scores": {
            "rsi": result.rsi_score,
            "macd": result.macd_score,
            "bollinger": result.bollinger_score,
            "stochastic": result.stochastic_score,
        },
        "indicators": {
            "rsi_value": result.rsi_value,
            "latest_close": result.latest_close,
        },
        "position": position_data,
        "trigger_reasons": trigger_reasons,
        "gemini_analysis": analysis,
        "telegram_sent": telegram_sent,
    }


@router.get("/{portfolio_id}/signals/history")
def get_signal_history(
    portfolio_id: int,
    ticker: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Son sinyal analizlerini döner (en yeni önce)."""
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    q = db.query(SignalAnalysis).filter(SignalAnalysis.portfolio_id == portfolio_id)
    if ticker:
        q = q.filter(SignalAnalysis.ticker == ticker.upper())

    records = q.order_by(SignalAnalysis.analyzed_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "ticker": r.ticker,
            "total_score": r.total_score,
            "triggered": r.triggered,
            "gemini_analysis": r.gemini_analysis,
            "telegram_sent": r.telegram_sent,
            "analyzed_at": r.analyzed_at.isoformat(),
            "scores": {
                "rsi": r.rsi_score,
                "macd": r.macd_score,
                "bollinger": r.bollinger_score,
                "stochastic": r.stochastic_score,
            },
            "indicators": {
                "rsi_value": float(r.rsi_value) if r.rsi_value else None,
                "latest_close": float(r.latest_close) if r.latest_close else None,
            },
        }
        for r in records
    ]
