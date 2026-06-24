import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import FundamentalReportAgent

report = FundamentalReportAgent().run("NVDA")

print("=" * 70)
print("Earnings rows:", len(report.earnings_table))
print("KPIs:", len(report.key_kpis))
print("Risks:", len(report.risk_factors_detail))
print("HTML length:", len(report.html_report))
print("=" * 70)

print("\n【財報表格前 4 行】\n")
for row in report.earnings_table[:4]:
    print(f"• {row.metric}")
    print(f"  Actual: {row.actual} | Consensus: {row.consensus} | YoY: {row.yoy_growth} | Result: {row.result}")
    print(f"  Commentary: {row.commentary}\n")

print("\n【風險因素 全部】\n")
for i, risk in enumerate(report.risk_factors_detail, 1):
    print(f"--- 風險 {i} [{risk.impact_level}] {risk.title} ---")
    print(f"描述: {risk.description}")
    print(f"影響: {risk.potential_impact}")
    print(f"監察: {risk.monitoring_signal}\n")

print("\n【投資總結與建議】\n")
print(f"整體看法: {report.overall_view}")
print(f"建議: {report.recommendation} ({report.confidence})")
print(f"買入價位: {report.suggested_buy_price}")
print(f"止盈價位: {report.take_profit_price}")
print(f"目標價區間: {report.target_price_range}")
print(f"止蝕價位: {report.stop_loss_price}")
print(f"\n目標價理由:\n{report.target_price_rationale}")
print(f"\n買入條件:\n{report.buy_conditions}")
print(f"\n持有條件:\n{report.hold_conditions}")
print(f"\n賣出條件:\n{report.sell_conditions}")
print(f"\n投資策略:\n{report.investment_strategy}")