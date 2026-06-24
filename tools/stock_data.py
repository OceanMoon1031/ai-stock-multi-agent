"""yfinance-based tools for fetching stock data."""

from __future__ import annotations

from typing import Any

import yfinance as yf

from tools.models import FinancialPeriod, Financials, StockInfo

# yfinance info keys mapped to our StockInfo fields
_INFO_FIELD_MAP: dict[str, str] = {
    "longName": "name",
    "shortName": "name",
    "currentPrice": "current_price",
    "regularMarketPrice": "current_price",
    "previousClose": "previous_close",
    "marketCap": "market_cap",
    "currency": "currency",
    "exchange": "exchange",
    "sector": "sector",
    "industry": "industry",
    "trailingPE": "pe_ratio",
    "forwardPE": "forward_pe",
    "trailingEps": "eps",
    "dividendYield": "dividend_yield",
    "beta": "beta",
    "fiftyTwoWeekHigh": "fifty_two_week_high",
    "fiftyTwoWeekLow": "fifty_two_week_low",
    "volume": "volume",
    "averageVolume": "avg_volume",
}

_FINANCIAL_SUMMARY_KEYS = (
    "totalRevenue",
    "revenuePerShare",
    "grossProfits",
    "ebitda",
    "netIncomeToCommon",
    "profitMargins",
    "operatingMargins",
    "returnOnAssets",
    "returnOnEquity",
    "totalCash",
    "totalDebt",
    "debtToEquity",
    "currentRatio",
    "freeCashflow",
    "operatingCashflow",
)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dataframe_to_periods(df: Any, max_periods: int = 4) -> list[FinancialPeriod]:
    """Convert a yfinance financial DataFrame into FinancialPeriod models."""
    if df is None or df.empty:
        return []

    periods: list[FinancialPeriod] = []
    for col in list(df.columns)[:max_periods]:
        period_label = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
        metrics: dict[str, float | None] = {}
        for row_name in df.index:
            metrics[str(row_name)] = _safe_float(df.at[row_name, col])
        periods.append(FinancialPeriod(period=period_label, metrics=metrics))
    return periods


def get_stock_info(ticker: str) -> StockInfo:
    """Fetch basic stock information for a given ticker symbol."""
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("Ticker symbol cannot be empty.")

    stock = yf.Ticker(symbol)
    info = stock.info or {}

    if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
        raise ValueError(f"No data found for ticker: {symbol}")

    data: dict[str, Any] = {"ticker": symbol}
    for yf_key, model_key in _INFO_FIELD_MAP.items():
        if yf_key not in info:
            continue
        value = info[yf_key]
        if model_key in ("market_cap", "volume", "avg_volume"):
            data[model_key] = _safe_int(value)
        else:
            data[model_key] = _safe_float(value) if model_key not in ("name", "currency", "exchange", "sector", "industry") else value

    if not data.get("name"):
        data["name"] = info.get("symbol", symbol)

    return StockInfo(**data)


def get_financials(ticker: str, max_periods: int = 4) -> Financials:
    """Fetch latest financial statement data for a given ticker symbol."""
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("Ticker symbol cannot be empty.")

    stock = yf.Ticker(symbol)
    info = stock.info or {}

    raw_summary = {
        key: info[key]
        for key in _FINANCIAL_SUMMARY_KEYS
        if key in info and info[key] is not None
    }

    financials = Financials(
        ticker=symbol,
        income_statement=_dataframe_to_periods(stock.financials, max_periods),
        balance_sheet=_dataframe_to_periods(stock.balance_sheet, max_periods),
        cash_flow=_dataframe_to_periods(stock.cashflow, max_periods),
        raw_summary=raw_summary,
    )

    if not financials.income_statement and not financials.balance_sheet and not financials.cash_flow and not raw_summary:
        raise ValueError(f"No financial data found for ticker: {symbol}")

    return financials