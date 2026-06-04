import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Portfolio

router = APIRouter()


@router.post("/{portfolio_id}/telegram/link")
def generate_telegram_link(portfolio_id: int, db: Session = Depends(get_db)):
    """
    Portföy için tek kullanımlık Telegram bağlantı linki üretir.
    Kullanıcı linke tıklayıp bota /start gönderince portföy otomatik bağlanır.
    """
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    token = uuid.uuid4().hex  # 32 karakterlik rastgele token
    portfolio.telegram_link_token = token
    db.commit()

    bot_username = "rtsm_notify_bot"
    deep_link_url = f"https://t.me/{bot_username}?start={token}"

    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        "telegram_url": deep_link_url,
        "already_linked": portfolio.telegram_chat_id is not None,
        "message": (
            "Linke tıklayın ve Telegram'da 'Başlat' butonuna basın. Bağlantı otomatik tamamlanacak."
        ),
    }


@router.delete("/{portfolio_id}/telegram/unlink")
def unlink_telegram(portfolio_id: int, db: Session = Depends(get_db)):
    """Portföyün Telegram bağlantısını koparır."""
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    portfolio.telegram_chat_id = None
    portfolio.telegram_link_token = None
    db.commit()

    return {"portfolio_id": portfolio_id, "message": "Telegram bağlantısı kaldırıldı."}


@router.get("/{portfolio_id}/telegram/status")
def telegram_status(portfolio_id: int, db: Session = Depends(get_db)):
    """Portföyün Telegram bağlantı durumunu döner."""
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return {
        "portfolio_id": portfolio_id,
        "linked": portfolio.telegram_chat_id is not None,
        "chat_id": portfolio.telegram_chat_id,
    }
