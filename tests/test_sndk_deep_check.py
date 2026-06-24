import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import DeepCheckAgent

report = DeepCheckAgent().run(
    "SNDK",
    available_capital="HK$300,000",
    risk_tolerance="平衡",
    investment_horizon="2-3年",
    portfolio_concentration="科技股佔組合約 40%",
)

print("Dimensions:", len(report.dimensions))
print("Missing check fields:")
fields = [
    ("1 management", report.management_quality),
    ("2 moat", report.moat_and_ai_leadership),
    ("3 macro", report.macro_geopolitics),
    ("4 sentiment", report.market_sentiment),
    ("5 technical", report.technical_timing),
    ("6 valuation", report.valuation_fairness),
    ("7 catalysts", report.catalysts_and_black_swans),
    ("8 personal", report.personal_fit),
]
for name, text in fields:
    print(f"  {name}: {len(text)} chars")

print("\n" + "=" * 70)
print(report.report_markdown)