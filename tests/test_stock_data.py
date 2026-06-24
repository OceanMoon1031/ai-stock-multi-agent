"""Tests for yfinance stock data tools."""

import pytest

from tools import get_financials, get_stock_info


def test_get_stock_info_returns_valid_model():
    info = get_stock_info("AAPL")
    assert info.ticker == "AAPL"
    assert info.name is not None
    assert info.current_price is not None
    assert info.current_price > 0


def test_get_financials_returns_valid_model():
    financials = get_financials("AAPL")
    assert financials.ticker == "AAPL"
    assert financials.income_statement or financials.raw_summary


def test_get_stock_info_empty_ticker_raises():
    with pytest.raises(ValueError, match="empty"):
        get_stock_info("  ")