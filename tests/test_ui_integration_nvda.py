"""Integration smoke test: both agents for NVDA with shared profile."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import DeepCheckAgent, FundamentalReportAgent

profile = {
    "available_capital": "HK$300,000",
    "risk_tolerance": "平衡",
    "investment_horizon": "2-3年",
    "portfolio_concentration": "科技股佔組合約 40%",
}

print("Running FundamentalReportAgent...")
fundamental = FundamentalReportAgent().run("NVDA")
print("  OK:", fundamental.ticker, fundamental.recommendation, len(fundamental.html_report))

print("Running DeepCheckAgent...")
deep = DeepCheckAgent().run(
    "NVDA",
    available_capital=profile["available_capital"],
    risk_tolerance=profile["risk_tolerance"],
    investment_horizon=profile["investment_horizon"],
    portfolio_concentration=profile["portfolio_concentration"],
)
print("  OK:", deep.ticker, deep.overall_rating, deep.suggested_position_size)

print("INTEGRATION OK")