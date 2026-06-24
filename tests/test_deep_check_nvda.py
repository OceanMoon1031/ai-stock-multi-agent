import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import DeepCheckAgent

agent = DeepCheckAgent()
report = agent.run(
    "NVDA",
    available_capital="HK$300,000",
    risk_tolerance="平衡",
    investment_horizon="2-3年",
    portfolio_concentration="科技股佔組合約 40%",
)

print("=" * 70)
print("Ticker:", report.ticker)
print("Dimensions:", len(report.dimensions))
print("Overall rating:", report.overall_rating)
print("Position size:", report.suggested_position_size)
print("=" * 70)

print("\n【整體評級】", report.overall_rating)
print("\n【建議倉位】", report.suggested_position_size)
print("\n【入場價區間】", report.entry_price_range)
print("\n【止蝕位】", report.stop_loss)
print("\n【主要買入理由】")
for reason in report.main_buy_reasons:
    print(f"  • {reason}")
print("\n【最大風險】")
print(report.max_risk)
print("\n【最終建議】")
print(report.final_recommendation)