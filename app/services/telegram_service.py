from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.services.signal_service import SignalResult

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

_INDICATOR_LABELS = {
    "rsi": "RSI",
    "macd": "MACD",
    "bollinger": "Bollinger Bands",
    "stochastic": "Stochastic",
}


def _indicator_detail(key: str, result: SignalResult, score: int) -> str:
    """Her indikatör için sinyal yönüne özel detay metni üretir."""
    if key == "rsi":
        rsi_display = f"{result.rsi_value:.1f}" if result.rsi_value is not None else "N/A"
        return f"RSI değeri: {rsi_display}"
    if key == "macd":
        return "kesişim yukarı" if score == 1 else "kesişim aşağı"
    if key == "bollinger":
        return "fiyat alt banda yakın" if score == 1 else "fiyat üst banda yakın"
    if key == "stochastic":
        return "%K < %D, 20 seviyesi" if score == 1 else "%K > %D, 80 seviyesi"
    return ""


def build_trigger_reasons(result: SignalResult) -> list[str]:
    """
    Her indikatörün durumunu 🟢/🔴/⚪ ile açıklar.
    Router hem yanıta hem Telegram mesajına bu listeyi kullanır.
    """
    indicators = [
        ("rsi", result.rsi_score),
        ("macd", result.macd_score),
        ("bollinger", result.bollinger_score),
        ("stochastic", result.stochastic_score),
    ]
    reasons = []
    for key, score in indicators:
        label = _INDICATOR_LABELS[key]
        if score == 1:
            detail = _indicator_detail(key, result, score)
            reasons.append(f"🟢 {label} → ALIM sinyali ({detail})")
        elif score == -1:
            detail = _indicator_detail(key, result, score)
            reasons.append(f"🔴 {label} → SATIM sinyali ({detail})")
        else:
            reasons.append(f"⚪ {label} → Nötr")
    return reasons


def _md_to_html(text: str) -> str:
    """Gemini'den gelen **bold** ve *italic* markdown'ı Telegram HTML'ine çevirir."""
    import re

    # **bold** → <b>bold</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    # *italic* → <i>italic</i>  (sadece tek yıldız kalanlar)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text, flags=re.DOTALL)
    # Telegram HTML'inde & < > kaçırılmalı (Gemini çıktısında nadiren olur ama önlem)
    # Önceden dönüştürülmüş tag'leri korumak için sadece düz metindeki karakterleri kaçır
    return text


def _build_message(result: SignalResult, gemini_analysis: str, trigger_reasons: list[str]) -> str:
    direction = "🟢 ALIM" if result.total_score > 0 else "🔴 SATIM"
    close_display = f"{result.latest_close:.2f}" if result.latest_close is not None else "N/A"
    reasons_text = "\n".join(trigger_reasons)
    analysis_text = (
        _md_to_html(gemini_analysis) if gemini_analysis else "<i>(analiz mevcut değil)</i>"
    )

    return (
        f"📊 <b>{result.ticker} — {direction} SİNYALİ</b>\n"
        f"Toplam Skor: <b>{result.total_score:+d}/4</b> | Son Kapanış: <b>{close_display}</b>\n\n"
        f"<b>Tetiklenme Sebebi:</b>\n"
        f"{reasons_text}\n\n"
        f"<b>Gemini Analizi:</b>\n"
        f"{analysis_text}"
    )


def send_signal_notification(
    result: SignalResult,
    gemini_analysis: str,
    chat_id: str | None = None,
) -> bool:
    """
    Sinyal bildirimini Telegram'a gönderir.

    `chat_id` verilirse (portföye özel) onu kullanır;
    verilmezse settings.telegram_chat_id'ye (global) döner.
    İkisi de yoksa sessizce False döner.
    """
    resolved_chat_id = chat_id or settings.telegram_chat_id
    if not settings.telegram_bot_token or not resolved_chat_id:
        logger.warning("Telegram credentials not set; skipping notification")
        return False
    try:
        trigger_reasons = build_trigger_reasons(result)
        url = _TELEGRAM_API.format(token=settings.telegram_bot_token)
        payload = {
            "chat_id": resolved_chat_id,
            "text": _build_message(result, gemini_analysis, trigger_reasons),
            "parse_mode": "HTML",
        }
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload)
        if resp.status_code != 200:
            logger.error("Telegram API returned %s: %s", resp.status_code, resp.text)
            return False
        return True
    except Exception:
        logger.exception("Telegram notification failed for ticker %s", result.ticker)
        return False
