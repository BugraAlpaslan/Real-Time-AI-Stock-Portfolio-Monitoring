from __future__ import annotations

import logging

from app.config import settings
from app.services.signal_service import SignalResult

logger = logging.getLogger(__name__)


def _build_prompt(result: SignalResult, position_data: dict | None = None) -> str:
    rsi_display   = f"{result.rsi_value:.1f}" if result.rsi_value is not None else "N/A"
    close_display = f"{result.latest_close:.2f}" if result.latest_close is not None else "N/A"

    rsi_interp = (
        "aşırı satım bölgesinde — alıcılar henüz devreye girmemiş, momentum baskı altında"
        if result.rsi_score == 1
        else "aşırı alım bölgesinde — momentum zirveye yakın, kâr realizasyonu başlayabilir"
        if result.rsi_score == -1
        else "nötr, belirgin bir aşırılık yok"
    )
    macd_interp = (
        "yukarı kesti — kısa vadeli ivme pozitife döndü, trend dönüşü denenebilir"
        if result.macd_score == 1
        else "aşağı kesti — kısa vadeli ivme negatife döndü, baskı artıyor"
        if result.macd_score == -1
        else "kesişim yok, mevcut trendin devamı bekleniyor"
    )
    bb_interp = (
        "alt banda dayandı — istatistiksel olarak ucuz bölge, geçmişte destek görülmüş"
        if result.bollinger_score == 1
        else "üst banda yapıştı — istatistiksel olarak pahalı bölge, geçmişte baskı gelmiş"
        if result.bollinger_score == -1
        else "bantların ortasında, fiyat normal aralıkta"
    )
    stoch_interp = (
        "%K aşırı satım altında yukarı kesti — kısa vadeli toparlanma refleksi gözlenebilir"
        if result.stochastic_score == 1
        else "%K aşırı alım üzerinde aşağı kesti — kısa vadeli düzeltme baskısı artıyor"
        if result.stochastic_score == -1
        else "aşırı bölge dışında, kesişim yok"
    )

    direction   = "ALIM" if result.total_score > 0 else "SATIM" if result.total_score < 0 else "NÖTR"
    confluence  = abs(result.total_score)
    signal_str  = f"{confluence}/4 indikatör {direction} yönünde hizalanmış"

    # Pozisyon bölümü
    position_section = ""
    if position_data:
        pnl_sign = "+" if position_data["unrealized_pnl"] >= 0 else ""
        position_section = (
            f"\nKullanıcının mevcut pozisyonu:\n"
            f"- Ortalama maliyet: {position_data['average_cost']:.2f}\n"
            f"- Adet: {position_data['quantity']:.4f}\n"
            f"- Toplam maliyet: {position_data['total_cost']:.2f}\n"
            f"- Anlık değer: {position_data['current_value']:.2f}\n"
            f"- Gerçekleşmemiş K/Z: {pnl_sign}{position_data['unrealized_pnl']:.2f} "
            f"({pnl_sign}{position_data['pnl_pct']:.1f}%)\n"
        )

    return (
        f"Deneyimli bir teknik analist olarak {result.ticker} hissesini değerlendiriyorsun.\n\n"
        f"Teknik tablo (son kapanış: {close_display}):\n"
        f"- RSI ({rsi_display}): {rsi_interp}\n"
        f"- MACD: {macd_interp}\n"
        f"- Bollinger: {bb_interp}\n"
        f"- Stochastic: {stoch_interp}\n\n"
        f"Genel sinyal: {signal_str}.\n"
        f"{position_section}\n"
        f"Şu iki bölümü Türkçe olarak yaz:\n\n"
        f"**Piyasa Yorumu** (2-3 cümle):\n"
        f"İndikatörlerin birlikte ne anlattığını, varsa çelişkileri, "
        f"piyasanın hisseyi nasıl fiyatladığını açıkla. Sayıları tekrarlama.\n\n"
        f"**Alınabilecek Aksiyonlar** (2-3 madde, • ile):\n"
        f"Teknik tabloya göre bir yatırımcının dikkat etmesi gereken seviyeleri, "
        f"olası senaryoları ve risk noktalarını belirt. "
        f"{'Kullanıcının açık pozisyonu var; bunu da göz önünde bulundur.' if position_data else ''} "
        f"Kesin al/sat tavsiyesi verme, senaryo bazlı konuş."
    )


_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)


def generate_analysis(result: SignalResult, position_data: dict | None = None) -> str:
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set; skipping Gemini analysis")
        return ""
    try:
        import httpx

        payload = {"contents": [{"parts": [{"text": _build_prompt(result, position_data)}]}]}
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": settings.gemini_api_key,
        }
        with httpx.Client(timeout=30) as client:
            resp = client.post(_GEMINI_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        logger.exception("Gemini API call failed for ticker %s", result.ticker)
        return ""
