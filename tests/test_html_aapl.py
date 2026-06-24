import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import FundamentalReportAgent

agent = FundamentalReportAgent()
report = agent.run("AAPL")

print("HTML length:", len(report.html_report))
print("Has dark theme:", "#0f172a" in report.html_report)
print("Has KPI grid:", "kpi-grid" in report.html_report)
print("Has risk cards:", "risk-card" in report.html_report)
print("Has earnings table:", "Latest Earnings Summary" in report.html_report)
print("\n--- HTML preview (first 1500 chars) ---\n")
print(report.html_report[:1500])