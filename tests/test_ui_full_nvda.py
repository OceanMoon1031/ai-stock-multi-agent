"""Integration test mirroring UI: technical only + full 3-step analysis."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import DeepCheckAgent, FundamentalReportAgent, TechnicalAnalysisAgent

TICKER = "NVDA"
PROFILE = {
    "available_capital": "HK$300,000",
    "risk_tolerance": "平衡",
    "investment_horizon": "2-3年",
    "portfolio_concentration": "科技股佔組合約 40%",
}

print("=== Test 1: Technical only ===")
technical = TechnicalAnalysisAgent().run(TICKER)
assert technical.ticker == TICKER
assert technical.report_markdown
assert technical.technical_rating
print("OK technical:", technical.technical_rating, technical.suitable_for_entry)

print("\n=== Test 2: Full analysis Step 1 → 2 → 3 ===")
fundamental = FundamentalReportAgent().run(TICKER)
print("OK step1:", fundamental.recommendation)

deep = DeepCheckAgent().run(TICKER, **PROFILE)
print("OK step2:", deep.overall_rating)

technical2 = TechnicalAnalysisAgent().run(TICKER)
print("OK step3:", technical2.technical_rating)

print("\n=== Tab content check ===")
for name, report in [
    ("基本面", fundamental),
    ("深度檢查", deep),
    ("技術面", technical2),
]:
    assert report.report_markdown.strip(), f"{name} markdown empty"
    print(f"  {name} markdown length:", len(report.report_markdown))

print("\nALL UI INTEGRATION TESTS PASSED")