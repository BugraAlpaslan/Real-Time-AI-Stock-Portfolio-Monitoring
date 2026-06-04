"""
Telegram Bot Polling Servisi

Webhook gerektirmez; FastAPI lifespan'inde arka planda çalışır.
Bot'a gelen her /start {token} mesajını yakalar ve portfolio'yu bağlar.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
_POLL_INTERVAL = 2  # saniye
_TIMEOUT = 30       # long-polling timeout (Telegram sunucu tarafında bekler)

_running = False


def _url(method: str) -> str:
    return _TELEGRAM_API.format(token=settings.telegram_bot_token, method=method)


async def _get_updates(client: httpx.AsyncClient, offset: int) -> list[dict]:
    try:
        resp = await client.get(
            _url("getUpdates"),
            params={"offset": offset, "timeout": _TIMEOUT, "allowed_updates": ["message"]},
            timeout=_TIMEOUT + 5,
        )
        if resp.status_code == 200:
            return resp.json().get("result", [])
    except Exception:
        logger.debug("Telegram getUpdates geçici hata, yeniden deneniyor...")
    return []


async def _send_message(client: httpx.AsyncClient, chat_id: int | str, text: str) -> None:
    try:
        await client.post(
            _url("sendMessage"),
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        logger.warning("Telegram mesaj gönderilemedi: chat_id=%s", chat_id)


async def _handle_start(chat_id: int, token: str) -> None:
    """
    /start {token} komutunu işler:
    - token'ı portfolio'da arar
    - eşleşirse chat_id kaydeder ve onay mesajı gönderir
    """
    from app.database import SessionLocal
    from app.models import Portfolio

    async with httpx.AsyncClient() as client:
        db = SessionLocal()
        try:
            portfolio = db.query(Portfolio).filter(
                Portfolio.telegram_link_token == token
            ).first()

            if portfolio is None:
                await _send_message(
                    client, chat_id,
                    "❌ Geçersiz veya süresi dolmuş bağlantı kodu.\n"
                    "Lütfen uygulamadan yeni bir bağlantı linki oluşturun."
                )
                return

            portfolio.telegram_chat_id = str(chat_id)
            portfolio.telegram_link_token = None   # tek kullanımlık — sil
            db.commit()

            await _send_message(
                client, chat_id,
                f"✅ *{portfolio.name}* portföyü başarıyla bağlandı!\n\n"
                "Bundan böyle bu portföy için sinyal bildirimleri buraya gelecek. 📊"
            )
            logger.info("Telegram bağlandı: portfolio_id=%s chat_id=%s", portfolio.id, chat_id)
        finally:
            db.close()


async def _process_update(update: dict) -> None:
    message = update.get("message", {})
    text: str = message.get("text", "")
    chat_id: int | None = message.get("chat", {}).get("id")

    if not text or chat_id is None:
        return

    # /start {token} formatı
    if text.startswith("/start "):
        token = text[len("/start "):].strip()
        if token:
            await _handle_start(chat_id, token)
    elif text.strip() == "/start":
        async with httpx.AsyncClient() as client:
            await _send_message(
                client, chat_id,
                "👋 Merhaba! Bu bot *RTSM* sinyal bildirimleri için kullanılır.\n\n"
                "Portföyünüzü bağlamak için uygulamadaki *Telegram Bağla* butonuna tıklayın."
            )


async def start_polling() -> None:
    """
    FastAPI lifespan'inden çağrılır. Token yoksa sessizce çıkar.
    """
    if not settings.telegram_bot_token:
        logger.info("TELEGRAM_BOT_TOKEN tanımlı değil; polling başlatılmadı.")
        return

    global _running
    _running = True
    offset = 0
    logger.info("Telegram polling başladı (@rtsm_notify_bot)")

    async with httpx.AsyncClient() as client:
        while _running:
            updates = await _get_updates(client, offset)
            for update in updates:
                await _process_update(update)
                offset = update["update_id"] + 1
            if not updates:
                await asyncio.sleep(_POLL_INTERVAL)


def stop_polling() -> None:
    global _running
    _running = False
