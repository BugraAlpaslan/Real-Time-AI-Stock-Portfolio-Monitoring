from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from app.services.signal_service import (
    _score_bollinger,
    _score_macd,
    _score_rsi,
    _score_stochastic,
    compute_signal_score,
    fetch_ohlcv,
)


# ---------- Yardımcılar ----------

def _make_df(**cols) -> pd.DataFrame:
    """Verilen sütunlarla minimal bir DataFrame oluşturur."""
    length = max(len(v) for v in cols.values())
    data = {k: ([float("nan")] * (length - len(v)) + list(v)) for k, v in cols.items()}
    return pd.DataFrame(data)


# ---------- fetch_ohlcv ----------

def test_fetch_ohlcv_empty_raises():
    with patch("app.services.signal_service.yf.download", return_value=pd.DataFrame()):
        with pytest.raises(ValueError, match="No OHLCV data"):
            fetch_ohlcv("INVALID")


def test_fetch_ohlcv_returns_lowercase_columns():
    mock_df = pd.DataFrame(
        {"Close": [100.0], "Open": [99.0], "High": [101.0], "Low": [98.0], "Volume": [1000]}
    )
    with patch("app.services.signal_service.yf.download", return_value=mock_df):
        df = fetch_ohlcv("AAPL")
    assert "close" in df.columns


# ---------- _score_rsi ----------

@pytest.mark.parametrize(
    "rsi_val, expected",
    [
        (28.0, 1),    # aşırı satım → AL
        (33.0, 1),    # eşik dahil → AL
        (50.0, 0),    # nötr
        (67.0, -1),   # eşik dahil → SAT
        (71.2, -1),   # aşırı alım → SAT
        (float("nan"), 0),  # eksik veri → nötr
    ],
)
def test_score_rsi(rsi_val, expected):
    df = _make_df(rsi=[rsi_val])
    assert _score_rsi(df) == expected


# ---------- _score_macd ----------

def test_score_macd_bullish_crossover():
    # önceki: macd < sinyal  →  şimdiki: macd > sinyal  ⟹ +1
    df = _make_df(macd=[-0.5, 0.3], macd_signal=[0.0, 0.1])
    assert _score_macd(df) == 1


def test_score_macd_bearish_crossover():
    # önceki: macd > sinyal  →  şimdiki: macd < sinyal  ⟹ -1
    df = _make_df(macd=[0.5, -0.1], macd_signal=[0.2, 0.0])
    assert _score_macd(df) == -1


def test_score_macd_no_crossover():
    # macd sürekli sinyal üstünde → 0
    df = _make_df(macd=[0.3, 0.4], macd_signal=[0.1, 0.2])
    assert _score_macd(df) == 0


def test_score_macd_insufficient_data():
    df = _make_df(macd=[0.3], macd_signal=[0.1])
    assert _score_macd(df) == 0


def test_score_macd_nan_returns_zero():
    df = _make_df(macd=[float("nan"), 0.3], macd_signal=[0.1, 0.2])
    assert _score_macd(df) == 0


# ---------- _score_bollinger ----------

def test_score_bollinger_lower_touch():
    # close ≈ bb_lower  ⟹ +1
    df = _make_df(close=[100.0], bb_lower=[100.2], bb_upper=[110.0])
    assert _score_bollinger(df) == 1


def test_score_bollinger_upper_touch():
    # close ≈ bb_upper  ⟹ -1
    df = _make_df(close=[110.0], bb_lower=[100.0], bb_upper=[109.8])
    assert _score_bollinger(df) == -1


def test_score_bollinger_middle():
    df = _make_df(close=[105.0], bb_lower=[100.0], bb_upper=[110.0])
    assert _score_bollinger(df) == 0


def test_score_bollinger_nan():
    df = _make_df(close=[105.0], bb_lower=[float("nan")], bb_upper=[110.0])
    assert _score_bollinger(df) == 0


# ---------- _score_stochastic ----------

def test_score_stochastic_bullish_crossover():
    # k önceki ≤ d, şimdiki k > d, şimdiki k < 20  ⟹ +1
    df = _make_df(stoch_k=[12.0, 16.0], stoch_d=[15.0, 14.0])
    assert _score_stochastic(df) == 1


def test_score_stochastic_bearish_crossover():
    # k önceki ≥ d, şimdiki k < d, şimdiki k > 80  ⟹ -1
    df = _make_df(stoch_k=[85.0, 82.0], stoch_d=[83.0, 84.0])
    assert _score_stochastic(df) == -1


def test_score_stochastic_neutral():
    df = _make_df(stoch_k=[50.0, 51.0], stoch_d=[49.0, 50.0])
    assert _score_stochastic(df) == 0


def test_score_stochastic_insufficient_data():
    df = _make_df(stoch_k=[15.0], stoch_d=[16.0])
    assert _score_stochastic(df) == 0


# ---------- compute_signal_score ----------

def _build_mock_df():
    """
    _compute_indicators mock'u bu df'i döndürür; compute_signal_score
    son satırdan rsi ve close okuyacağı için her iki sütun da bulunmalı.
    """
    n = 30
    closes = [100.0 + i * 0.1 for i in range(n)]
    df = pd.DataFrame({
        "open": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
        "volume": [1_000_000] * n,
        "rsi": [28.0] * n,
    })
    return df


@patch("app.services.signal_service.yf.download")
@patch("app.services.signal_service._compute_indicators")
@patch("app.services.signal_service._score_rsi", return_value=1)
@patch("app.services.signal_service._score_macd", return_value=1)
@patch("app.services.signal_service._score_bollinger", return_value=0)
@patch("app.services.signal_service._score_stochastic", return_value=0)
def test_compute_signal_score_triggered(
    mock_stoch, mock_bb, mock_macd, mock_rsi, mock_indicators, mock_download
):
    mock_df = _build_mock_df()
    mock_download.return_value = mock_df
    mock_indicators.return_value = mock_df

    result = compute_signal_score("AAPL")

    assert result.ticker == "AAPL"
    assert result.total_score == 2
    assert result.triggered is True
    assert result.rsi_score == 1
    assert result.macd_score == 1


@patch("app.services.signal_service.yf.download")
@patch("app.services.signal_service._compute_indicators")
@patch("app.services.signal_service._score_rsi", return_value=0)
@patch("app.services.signal_service._score_macd", return_value=0)
@patch("app.services.signal_service._score_bollinger", return_value=0)
@patch("app.services.signal_service._score_stochastic", return_value=0)
def test_compute_signal_score_not_triggered(
    mock_stoch, mock_bb, mock_macd, mock_rsi, mock_indicators, mock_download
):
    mock_df = _build_mock_df()
    mock_download.return_value = mock_df
    mock_indicators.return_value = mock_df

    result = compute_signal_score("AAPL")

    assert result.total_score == 0
    assert result.triggered is False
