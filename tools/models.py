"""Pydantic models for structured stock data output."""

from typing import Any

from pydantic import BaseModel, Field


class StockInfo(BaseModel):
    """Basic stock information from yfinance."""

    ticker: str
    name: str | None = None
    current_price: float | None = None
    previous_close: float | None = None
    market_cap: int | None = None
    currency: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    pe_ratio: float | None = Field(default=None, description="Trailing P/E ratio")
    forward_pe: float | None = None
    eps: float | None = Field(default=None, description="Trailing EPS")
    dividend_yield: float | None = None
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    volume: int | None = None
    avg_volume: int | None = None


class FinancialPeriod(BaseModel):
    """Financial metrics for a single reporting period."""

    period: str
    metrics: dict[str, float | None] = Field(default_factory=dict)


class Financials(BaseModel):
    """Latest financial statements from yfinance."""

    ticker: str
    income_statement: list[FinancialPeriod] = Field(default_factory=list)
    balance_sheet: list[FinancialPeriod] = Field(default_factory=list)
    cash_flow: list[FinancialPeriod] = Field(default_factory=list)
    raw_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Key financial highlights from ticker.info",
    )


class TechnicalIndicatorSnapshot(BaseModel):
    """Computed technical indicators from historical price data."""

    ticker: str
    as_of: str
    latest_close: float | None = None
    previous_close: float | None = None
    change_pct_1d: float | None = None
    change_pct_5d: float | None = None
    change_pct_20d: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    volume: int | None = None
    avg_volume_20: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    distance_from_52w_high_pct: float | None = None
    distance_from_52w_low_pct: float | None = None
    trend_vs_sma20: str | None = None
    trend_vs_sma50: str | None = None
    trend_vs_sma200: str | None = None