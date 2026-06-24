"""Technical indicator calculations using yfinance + pandas + ta."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator

from tools.models import TechnicalIndicatorSnapshot

HKT = ZoneInfo("Asia/Hong_Kong")


def _safe_float(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _price_vs_ma(price: float | None, ma: float | None) -> str | None:
    if price is None or ma is None or ma == 0:
        return None
    if price > ma * 1.01:
        return "above"
    if price < ma * 0.99:
        return "below"
    return "near"


def calculate_technical_indicators(ticker: str, period: str = "1y") -> TechnicalIndicatorSnapshot:
    """Fetch historical prices and compute RSI, MACD, and moving averages."""
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("Ticker symbol cannot be empty.")

    stock = yf.Ticker(symbol)
    history = stock.history(period=period, interval="1d", auto_adjust=True)
    info = stock.info or {}

    if history is None or history.empty:
        raise ValueError(f"No historical price data found for ticker: {symbol}")

    df = history.copy()
    close = df["Close"]
    volume = df["Volume"]

    latest_close = _safe_float(close.iloc[-1])
    previous_close = _safe_float(close.iloc[-2]) if len(close) > 1 else None

    change_1d = None
    if latest_close is not None and previous_close not in (None, 0):
        change_1d = ((latest_close - previous_close) / previous_close) * 100

    change_5d = None
    if len(close) > 5 and close.iloc[-6] != 0:
        change_5d = ((close.iloc[-1] - close.iloc[-6]) / close.iloc[-6]) * 100

    change_20d = None
    if len(close) > 20 and close.iloc[-21] != 0:
        change_20d = ((close.iloc[-1] - close.iloc[-21]) / close.iloc[-21]) * 100

    rsi_14 = None
    if len(close) >= 15:
        rsi_14 = _safe_float(RSIIndicator(close=close, window=14).rsi().iloc[-1])

    macd_val = macd_signal = macd_hist = None
    if len(close) >= 35:
        macd_ind = MACD(close=close)
        macd_val = _safe_float(macd_ind.macd().iloc[-1])
        macd_signal = _safe_float(macd_ind.macd_signal().iloc[-1])
        macd_hist = _safe_float(macd_ind.macd_diff().iloc[-1])

    sma_20 = sma_50 = sma_200 = None
    if len(close) >= 20:
        sma_20 = _safe_float(SMAIndicator(close=close, window=20).sma_indicator().iloc[-1])
    if len(close) >= 50:
        sma_50 = _safe_float(SMAIndicator(close=close, window=50).sma_indicator().iloc[-1])
    if len(close) >= 200:
        sma_200 = _safe_float(SMAIndicator(close=close, window=200).sma_indicator().iloc[-1])

    latest_volume = int(volume.iloc[-1]) if not pd.isna(volume.iloc[-1]) else None
    avg_volume_20 = _safe_float(volume.tail(20).mean()) if len(volume) >= 20 else None

    high_52w = _safe_float(info.get("fiftyTwoWeekHigh")) or _safe_float(close.max())
    low_52w = _safe_float(info.get("fiftyTwoWeekLow")) or _safe_float(close.min())

    dist_high = dist_low = None
    if latest_close is not None and high_52w not in (None, 0):
        dist_high = ((latest_close - high_52w) / high_52w) * 100
    if latest_close is not None and low_52w not in (None, 0):
        dist_low = ((latest_close - low_52w) / low_52w) * 100

    as_of = datetime.now(HKT).strftime("截至%Y年%m月%d日 %H:%M HKT")

    return TechnicalIndicatorSnapshot(
        ticker=symbol,
        as_of=as_of,
        latest_close=latest_close,
        previous_close=previous_close,
        change_pct_1d=change_1d,
        change_pct_5d=change_5d,
        change_pct_20d=change_20d,
        rsi_14=rsi_14,
        macd=macd_val,
        macd_signal=macd_signal,
        macd_histogram=macd_hist,
        sma_20=sma_20,
        sma_50=sma_50,
        sma_200=sma_200,
        volume=latest_volume,
        avg_volume_20=avg_volume_20,
        fifty_two_week_high=high_52w,
        fifty_two_week_low=low_52w,
        distance_from_52w_high_pct=dist_high,
        distance_from_52w_low_pct=dist_low,
        trend_vs_sma20=_price_vs_ma(latest_close, sma_20),
        trend_vs_sma50=_price_vs_ma(latest_close, sma_50),
        trend_vs_sma200=_price_vs_ma(latest_close, sma_200),
    )