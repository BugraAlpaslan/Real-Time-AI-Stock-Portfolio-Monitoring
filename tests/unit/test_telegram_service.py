from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from app.services.signal_service import SignalResult
from app.services.telegram_service import (
    _build_message,
    build_trigger_reasons,
    send_signal_notification,
)


# ---------- Yardımcı ----------

def _make_result(
    rsi=1, macd=1, bollinger=0, stochastic=0,
    rsi_value=28.4, latest_close=213.7,
    ticker="AAPL",
) -> SignalResult:
    total = rsi + macd + bollinger + stochastic
    return SignalResult(
        ticker=ticker,
        rsi_score=rsi,
        macd_score=macd,
        bollinger_score=bollinger,
        stochastic_score=stochastic,
        total_score=total,
        rsi_value=rsi_value,
        latest_close=latest_close,
        triggered=abs(total) >= 2,
    )


# ---------- build_trigger_reasons ----------

def test_build_trigger_reasons_all_buy():
    result = _make_result(rsi=1, macd=1, bollinger=1, stochastic=1)
    reasons = build_trigger_reasons(result)
    assert len(reasons) == 4
    assert all("🟢" in r for r in reasons)
    assert all("ALIM" in r for r in reasons)


def test_build_trigger_reasons_all_sell():
    result = _make_result(rsi=-1, macd=-1, bollinger=-1, stochastic=-1, rsi_value=71.0)
    reasons = build_trigger_reasons(result)
    assert len(reasons) == 4
    assert all("🔴" in r for r in reasons)
    assert all("SATIM" in r for r in reasons)


def test_build_trigger_reasons_neutral():
    result = _make_result(rsi=0, macd=0, bollinger=0, stochastic=0)
    reasons = build_trigger_reasons(result)
    assert all("⚪" in r for r in reasons)
    assert all("Nötr" in r for r in reasons)


def test_build_trigger_reasons_mixed():
    result = _make_result(rsi=1, macd=-1, bollinger=0, stochastic=1)
    reasons = build_trigger_reasons(result)
    assert "🟢" in reasons[0]   # RSI → AL
    assert "🔴" in reasons[1]   # MACD → SAT
    assert "⚪" in reasons[2]   # Bollinger → Nötr
    assert "🟢" in reasons[3]   # Stochastic → AL


def test_build_trigger_reasons_rsi_value_displayed():
    result = _make_result(rsi=1, rsi_value=28.4)
    reasons = build_trigger_reasons(result)
    assert "28.4" in reasons[0]


def test_build_trigger_reasons_rsi_value_none():
    result = _make_result(rsi=1, rsi_value=None)
    reasons = build_trigger_reasons(result)
    assert "N/A" in reasons[0]


# ---------- _build_message ----------

def test_build_message_buy_direction():
    result = _make_result(rsi=1, macd=1)
    reasons = build_trigger_reasons(result)
    msg = _build_message(result, "Test analiz.", reasons)
    assert "🟢 ALIM" in msg
    assert "AAPL" in msg
    assert "Test analiz." in msg


def test_build_message_sell_direction():
    result = _make_result(rsi=-1, macd=-1, bollinger=-1, stochastic=-1, rsi_value=71.0)
    reasons = build_trigger_reasons(result)
    msg = _build_message(result, "", reasons)
    assert "🔴 SATIM" in msg


def test_build_message_no_gemini_analysis():
    result = _make_result()
    reasons = build_trigger_reasons(result)
    msg = _build_message(result, "", reasons)
    assert "<i>(analiz mevcut değil)</i>" in msg


def test_build_message_contains_close_price():
    result = _make_result(latest_close=213.7)
    reasons = build_trigger_reasons(result)
    msg = _build_message(result, "", reasons)
    assert "213.70" in msg


# ---------- send_signal_notification ----------

def test_send_notification_no_token(monkeypatch):
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_bot_token", None)
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_chat_id", "123")
    result = _make_result()
    assert send_signal_notification(result, "") is False


def test_send_notification_no_chat_id(monkeypatch):
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_bot_token", "token")
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_chat_id", None)
    result = _make_result()
    assert send_signal_notification(result, "") is False


def test_send_notification_http_200(monkeypatch):
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_bot_token", "tok")
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_chat_id", "123")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("app.services.telegram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = _make_result()
        assert send_signal_notification(result, "analiz") is True


def test_send_notification_http_400(monkeypatch):
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_bot_token", "tok")
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_chat_id", "123")

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"

    with patch("app.services.telegram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = _make_result()
        assert send_signal_notification(result, "") is False


def test_send_notification_timeout_returns_false(monkeypatch):
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_bot_token", "tok")
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_chat_id", "123")

    with patch("app.services.telegram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_client_cls.return_value = mock_client

        result = _make_result()
        assert send_signal_notification(result, "") is False
