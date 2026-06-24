import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import FundamentalReportAgent

agent = FundamentalReportAgent()
report = agent.run("NVDA")

print("=" * 70)
print("Ticker:", report.ticker)
print("Earnings rows:", len(report.earnings_table))
print("KPIs:", len(report.key_kpis))
print("Risks:", len(report.risk_factors_detail))
print("Segments:", len(report.segment_breakdown))
print("Guidance items:", len(report.guidance_comparison))
print("HTML length:", len(report.html_report))
print("=" * 70)

print("\n【執行摘要】\n")
print(report.executive_summary)

print("\n【財報表格 earnings_table】\n")
for row in report.earnings_table:
    print(f"- {row.metric} | Actual: {row.actual} | Consensus: {row.consensus} | YoY: {row.yoy_growth} | Result: {row.result}")

print("\n【KPI】\n")
for kpi in report.key_kpis:
    print(f"- {kpi.name}: {kpi.value} — {kpi.assessment}")

print("\n【風險因素】\n")
for risk in report.risk_factors_detail:
    print(f"- [{risk.impact_level}] {risk.title}: {risk.description[:120]}...")

# Extract HTML sections for preview
html = report.html_report
for section in ["執行摘要", "最新財報摘要", "關鍵 KPI", "主要風險因素"]:
    print(f"\nHTML contains '{section}':", section in html)