import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import TechnicalAnalysisAgent
from tools import calculate_technical_indicators

indicators = calculate_technical_indicators("NVDA")
print("Indicators RSI:", indicators.rsi_14, "MACD:", indicators.macd, "SMA20:", indicators.sma_20)

report = TechnicalAnalysisAgent().run("NVDA")

print("=" * 70)
print("Rating:", report.technical_rating)
print("Suitable:", report.suitable_for_entry)
print("Sections:", len(report.sections))
print("=" * 70)

print("\n【整體技術面總結 + 評級】")
print(report.overall_summary)
print(f"\n技術面評級：{report.technical_rating} | 適合入場：{report.suitable_for_entry}")

print("\n【入場策略建議】")
print(f"入場價區間：{report.entry_price_range}")
print(f"止蝕位：{report.stop_loss}")
print(f"止盈 1：{report.take_profit_1}")
print(f"止盈 2：{report.take_profit_2}")
print(f"倉位建議：{report.position_size}")
print(report.entry_strategy)

print("\n【風險提示】")
print(report.risk_warnings)