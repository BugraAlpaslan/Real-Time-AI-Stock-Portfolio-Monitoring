from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
import ta
import yfinance as yf

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SignalResult:
    ticker: str
    rsi_score: int
    macd_score: int
    bollinger_score: int
    stochastic_score: int
    total_score: int
    rsi_value: float | None
    latest_close: float | None
    triggered: bool


# ---------- Veri Katmanı ----------

def fetch_ohlcv(ticker: str, days: int | None = None) -> pd.DataFrame:
    days = days or settings.signal_history_days
    period = f"{days}d"
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        raise ValueError(f"No OHLCV data found for ticker '{ticker}'")
    # yfinance bazen MultiIndex döner; düzleştir
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df


# ---------- İndikatör Hesaplama ----------

def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # RSI (14)
    df["rsi"] = ta.momentum.RSIIndicator(close=close, window=14).rsi()

    # MACD (12, 26, 9)
    macd_obj = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd_obj.macd()
    df["macd_signal"] = macd_obj.macd_signal()

    # Bollinger Bands (20, 2)
    bb_obj = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    df["bb_lower"] = bb_obj.bollinger_lband()
    df["bb_upper"] = bb_obj.bollinger_hband()

    # Stochastic Oscillator (k=14, d=3, smooth=3)
    stoch_obj = ta.momentum.StochasticOscillator(
        high=high, low=low, close=close, window=14, smooth_window=3
    )
    df["stoch_k"] = stoch_obj.stoch()
    df["stoch_d"] = stoch_obj.stoch_signal()

    return df


# ---------- Puanlama ----------

def _score_rsi(df: pd.DataFrame) -> int:
    val = df["rsi"].iloc[-1]
    if pd.isna(val):
        return 0
    if val <= 33:
        return 1
    if val >= 67:
        return -1
    return 0


def _score_macd(df: pd.DataFrame) -> int:
    if len(df) < 2:
        return 0
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    if pd.isna(prev["macd"]) or pd.isna(curr["macd"]):
        return 0
    # Yukarı kesişim: önceki MACD ≤ sinyal, şimdiki MACD > sinyal
    if prev["macd"] <= prev["macd_signal"] and curr["macd"] > curr["macd_signal"]:
        return 1
    # Aşağı kesişim: önceki MACD ≥ sinyal, şimdiki MACD < sinyal
    if prev["macd"] >= prev["macd_signal"] and curr["macd"] < curr["macd_signal"]:
        return -1
    return 0


def _score_bollinger(df: pd.DataFrame) -> int:
    row = df.iloc[-1]
    close = row["close"]
    lower = row["bb_lower"]
    upper = row["bb_upper"]
    if pd.isna(lower) or pd.isna(upper):
        return 0
    tolerance = 0.005  # %0.5
    if abs(close - lower) / close <= tolerance:
        return 1
    if abs(close - upper) / close <= tolerance:
        return -1
    return 0


def _score_stochastic(df: pd.DataFrame) -> int:
    if len(df) < 2:
        return 0
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    if pd.isna(prev["stoch_k"]) or pd.isna(curr["stoch_k"]):
        return 0
    # %K, %D'yi 20 seviyesinin altında yukarı kesiyor
    if prev["stoch_k"] <= prev["stoch_d"] and curr["stoch_k"] > curr["stoch_d"] and curr["stoch_k"] < 20:
        return 1
    # %K, %D'yi 80 seviyesinin üzerinde aşağı kesiyor
    if prev["stoch_k"] >= prev["stoch_d"] and curr["stoch_k"] < curr["stoch_d"] and curr["stoch_k"] > 80:
        return -1
    return 0


# ---------- Ana Fonksiyon ----------

def compute_signal_score(ticker: str) -> SignalResult:
    df = fetch_ohlcv(ticker)
    df = _compute_indicators(df)

    rsi_score = _score_rsi(df)
    macd_score = _score_macd(df)
    bollinger_score = _score_bollinger(df)
    stochastic_score = _score_stochastic(df)
    total = rsi_score + macd_score + bollinger_score + stochastic_score

    rsi_val = df["rsi"].iloc[-1]
    close_val = df["close"].iloc[-1]

    return SignalResult(
        ticker=ticker,
        rsi_score=rsi_score,
        macd_score=macd_score,
        bollinger_score=bollinger_score,
        stochastic_score=stochastic_score,
        total_score=total,
        rsi_value=float(rsi_val) if not pd.isna(rsi_val) else None,
        latest_close=float(close_val) if not pd.isna(close_val) else None,
        triggered=abs(total) >= settings.signal_score_threshold,
    )
