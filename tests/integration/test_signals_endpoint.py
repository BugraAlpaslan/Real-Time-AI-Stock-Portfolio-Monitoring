from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.signal_service import SignalResult
from tests.factories import PortfolioFactory


def _triggered_result(ticker="AAPL") -> SignalResult:
    return SignalResult(
        ticker=ticker,
        rsi_score=1,
        macd_score=1,
        bollinger_score=0,
        stochastic_score=0,
        total_score=2,
        rsi_value=28.4,
        latest_close=213.7,
        triggered=True,
    )


def _neutral_result(ticker="AAPL") -> SignalResult:
    return SignalResult(
        ticker=ticker,
        rsi_score=0,
        macd_score=0,
        bollinger_score=0,
        stochastic_score=0,
        total_score=0,
        rsi_value=50.0,
        latest_close=213.7,
        triggered=False,
    )


# ---------- 404 — portfolio bulunamadı ----------

def test_signals_portfolio_not_found(client):
    with patch("app.services.signal_service.compute_signal_score", return_value=_triggered_result()):
        resp = client.get("/portfolios/99999/signals?ticker=AAPL")
    assert resp.status_code == 404


# ---------- 422 — ticker eksik ----------

def test_signals_missing_ticker(client):
    portfolio = PortfolioFactory()
    resp = client.get(f"/portfolios/{portfolio.id}/signals")
    assert resp.status_code == 422


# ---------- 503 — OHLCV verisi alınamadı ----------

def test_signals_ohlcv_failure(client):
    portfolio = PortfolioFactory()
    with patch(
        "app.services.signal_service.compute_signal_score",
        side_effect=ValueError("No OHLCV data found for ticker 'FAKE'"),
    ):
        resp = client.get(f"/portfolios/{portfolio.id}/signals?ticker=FAKE")
    assert resp.status_code == 503
    assert "No OHLCV data" in resp.json()["detail"]


# ---------- 200 — triggered=True, Gemini + Telegram mock ----------

def test_signals_triggered_success(client):
    portfolio = PortfolioFactory()
    with (
        patch("app.services.signal_service.compute_signal_score", return_value=_triggered_result()),
        patch("app.services.gemini_analysis_service.generate_analysis", return_value="Test analizi."),
        patch("app.services.telegram_service.send_signal_notification", return_value=True),
    ):
        resp = client.get(f"/portfolios/{portfolio.id}/signals?ticker=AAPL")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert data["triggered"] is True
    assert data["total_score"] == 2
    assert data["gemini_analysis"] == "Test analizi."
    assert data["telegram_sent"] is True
    assert len(data["trigger_reasons"]) == 4
    assert data["scores"]["rsi"] == 1
    assert data["scores"]["macd"] == 1
    assert data["indicators"]["rsi_value"] == pytest.approx(28.4)
    assert data["indicators"]["latest_close"] == pytest.approx(213.7)


# ---------- 200 — triggered=False, Gemini ve Telegram çağrılmaz ----------

def test_signals_not_triggered(client):
    portfolio = PortfolioFactory()
    with (
        patch("app.services.signal_service.compute_signal_score", return_value=_neutral_result()),
        patch("app.services.gemini_analysis_service.generate_analysis") as mock_gemini,
        patch("app.services.telegram_service.send_signal_notification") as mock_tg,
    ):
        resp = client.get(f"/portfolios/{portfolio.id}/signals?ticker=AAPL")

    assert resp.status_code == 200
    data = resp.json()
    assert data["triggered"] is False
    assert data["gemini_analysis"] == ""
    assert data["telegram_sent"] is False
    mock_gemini.assert_not_called()
    mock_tg.assert_not_called()


# ---------- 200 — Telegram token eksik, telegram_sent=False ama 200 döner ----------

def test_signals_telegram_not_configured(client, monkeypatch):
    monkeypatch.setattr("app.services.telegram_service.settings.telegram_bot_token", None)
    portfolio = PortfolioFactory()
    with (
        patch("app.services.signal_service.compute_signal_score", return_value=_triggered_result()),
        patch("app.services.gemini_analysis_service.generate_analysis", return_value="Analiz"),
    ):
        resp = client.get(f"/portfolios/{portfolio.id}/signals?ticker=AAPL")

    assert resp.status_code == 200
    assert resp.json()["telegram_sent"] is False


# ---------- trigger_reasons her zaman dolu ----------

def test_signals_trigger_reasons_always_present(client):
    portfolio = PortfolioFactory()
    with patch("app.services.signal_service.compute_signal_score", return_value=_neutral_result()):
        resp = client.get(f"/portfolios/{portfolio.id}/signals?ticker=AAPL")

    assert resp.status_code == 200
    reasons = resp.json()["trigger_reasons"]
    assert len(reasons) == 4
    assert all("Nötr" in r for r in reasons)
