"""HTML report builder for fundamental analysis."""

from __future__ import annotations

import html
import re
from typing import Any

from agents.models import (
    EarningsTableRow,
    FundamentalReport,
    GuidanceComparisonItem,
    KPIItem,
    RiskFactorDetail,
    SegmentItem,
)
from tools.models import Financials, StockInfo

DARK_BG = "#0f172a"
CARD_BG = "#1e2937"
TEXT_PRIMARY = "#f8fafc"
TEXT_MUTED = "#94a3b8"
GREEN = "#22c55e"
RED = "#ef4444"
ACCENT = "#38bdf8"
BORDER = "#334155"
YELLOW = "#eab308"


def _esc(text: Any) -> str:
    return html.escape(str(text) if text is not None else "—")


def _mono(text: Any) -> str:
    return f'<span class="mono">{_esc(text)}</span>'


def _paragraphs(text: str) -> str:
    chunks = [chunk.strip() for chunk in re.split(r"\n+", text or "") if chunk.strip()]
    if not chunks:
        return "<p>—</p>"
    return "".join(f"<p>{_esc(chunk)}</p>" for chunk in chunks)


def _view_color(view: str) -> str:
    return {"Bullish": GREEN, "Bearish": RED, "Neutral": YELLOW}.get(view, ACCENT)


def _impact_color(level: str) -> str:
    return {
        "高": RED,
        "中高": "#f97316",
        "中": YELLOW,
        "中低": "#84cc16",
        "低": GREEN,
    }.get(level, TEXT_MUTED)


def _result_cell(result: str) -> str:
    mapping = {
        "Beat": ("positive", "Beat / 超預期"),
        "Miss": ("negative", "Miss / 未達預期"),
        "Inline": ("inline", "Inline / 符合預期"),
        "N/A": ("na", "N/A / 數據不可用"),
    }
    css, label = mapping.get(result, ("na", _esc(result)))
    return f'<span class="{css}">{label}</span>'


def _format_large_number(value: float | None) -> str:
    if value is None:
        return "數據不可用"
    abs_val = abs(value)
    if abs_val >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    if abs_val >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs_val >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return f"{value:,.2f}"


def _metric_from_periods(
    financials: Financials,
    metric_names: tuple[str, ...],
) -> tuple[float | None, float | None]:
    if not financials.income_statement:
        return None, None
    latest = financials.income_statement[0]
    prior = financials.income_statement[1] if len(financials.income_statement) > 1 else None

    def pick(metrics: dict[str, float | None]) -> float | None:
        for name in metric_names:
            if name in metrics and metrics[name] is not None:
                return metrics[name]
        return None

    return pick(latest.metrics), pick(prior.metrics) if prior else None


def _yoy_string(current: float | None, prior: float | None) -> str:
    if current is None or prior in (None, 0):
        return "—"
    growth = ((current - prior) / abs(prior)) * 100
    sign = "+" if growth >= 0 else ""
    return f"{sign}{growth:.1f}%"


def _fallback_earnings_rows(financials: Financials) -> list[EarningsTableRow]:
    specs = [
        ("Revenue（營收）", ("Total Revenue", "Revenue")),
        ("Gross Profit（毛利）", ("Gross Profit",)),
        ("Operating Income（營業利潤）", ("Operating Income",)),
        ("GAAP Net Income（GAAP 淨利潤）", ("Net Income", "Net Income Common Stockholders")),
        ("Diluted EPS（稀釋每股盈利）", ("Diluted EPS", "Basic EPS")),
        ("R&D Expense（研發費用）", ("Research And Development", "Research Development")),
    ]
    rows: list[EarningsTableRow] = []
    for label, keys in specs:
        current, prior = _metric_from_periods(financials, keys)
        rows.append(
            EarningsTableRow(
                metric=label,
                actual=_format_large_number(current),
                consensus="數據不可用",
                yoy_growth=_yoy_string(current, prior),
                result="N/A",
                commentary="由 yfinance 財報數據自動提取；市場預期需另行數據源。",
            )
        )
    return rows


def _build_earnings_table(rows: list[EarningsTableRow]) -> str:
    body = []
    for row in rows:
        yoy_class = "positive" if row.yoy_growth.startswith("+") else "negative" if row.yoy_growth.startswith("-") else "na"
        body.append(
            f"""
            <tr>
              <td>
                <strong>{_esc(row.metric)}</strong>
                <div class="row-period">{_esc(row.period or "最新財年")}</div>
                <div class="row-comment">{_esc(row.commentary)}</div>
              </td>
              <td>{_mono(row.actual)}</td>
              <td>{_mono(row.consensus)}</td>
              <td><span class="{yoy_class}">{_esc(row.yoy_growth)}</span></td>
              <td>{_result_cell(row.result)}</td>
            </tr>
            """
        )
    return "\n".join(body)


def _build_kpi_cards(kpis: list[KPIItem]) -> str:
    if not kpis:
        return '<p class="muted">暫無 KPI 數據</p>'
    cards = []
    for index, kpi in enumerate(kpis, start=1):
        cards.append(
            f"""
            <div class="kpi-card">
              <div class="kpi-index">#{index}</div>
              <div class="kpi-name">{_esc(kpi.name)}</div>
              <div class="kpi-value">{_mono(kpi.value)}</div>
              <div class="kpi-assessment">{_esc(kpi.assessment)}</div>
            </div>
            """
        )
    return f'<div class="kpi-grid">{"".join(cards)}</div>'


def _build_segment_cards(segments: list[SegmentItem], fallback_text: str) -> str:
    if not segments:
        return _paragraphs(fallback_text)
    cards = []
    for seg in segments:
        cards.append(
            f"""
            <div class="segment-card">
              <h4>{_esc(seg.segment_name)}</h4>
              <p><strong>表現：</strong>{_esc(seg.performance_summary)}</p>
              <p><strong>AI 相關性：</strong>{_esc(seg.ai_relevance)}</p>
              <p><strong>增長展望：</strong>{_esc(seg.growth_outlook)}</p>
            </div>
            """
        )
    return f'<div class="segment-grid">{"".join(cards)}</div>'


def _build_guidance_table(items: list[GuidanceComparisonItem], fallback_text: str) -> str:
    if not items:
        return _paragraphs(fallback_text)
    rows = []
    for item in items:
        rows.append(
            f"""
            <tr>
              <td><strong>{_esc(item.metric)}</strong></td>
              <td>{_esc(item.company_guidance)}</td>
              <td>{_esc(item.market_expectation)}</td>
              <td>{_esc(item.gap_analysis)}</td>
            </tr>
            """
        )
    return f"""
    <table class="data-table">
      <thead>
        <tr>
          <th>指標 Metric</th>
          <th>公司指引 Guidance</th>
          <th>市場預期 Consensus</th>
          <th>差距分析 Gap Analysis</th>
        </tr>
      </thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    <div class="section-note">{_paragraphs(fallback_text)}</div>
    """


def _build_risk_cards(risks: list[RiskFactorDetail]) -> str:
    if not risks:
        return '<div class="risk-card"><p>暫無風險數據</p></div>'
    cards = []
    for index, risk in enumerate(risks, start=1):
        color = _impact_color(risk.impact_level)
        cards.append(
            f"""
            <div class="risk-card">
              <div class="risk-header">
                <h4>風險 {index}：{_esc(risk.title)}</h4>
                <span class="impact-badge" style="background:{color}22;color:{color};border:1px solid {color};">
                  影響程度：{_esc(risk.impact_level)}
                </span>
              </div>
              <div class="risk-body">
                <p><span class="label">風險描述 Risk Description</span>{_esc(risk.description)}</p>
                <p><span class="label">可能影響 Potential Impact</span>{_esc(risk.potential_impact)}</p>
                <p><span class="label">監察信號 Monitoring Signal</span>{_esc(risk.monitoring_signal or "—")}</p>
              </div>
            </div>
            """
        )
    return "\n".join(cards)


def _build_price_action_panel(report: FundamentalReport) -> str:
    levels = report.price_action_levels
    if not levels and report.investment_detail:
        levels = report.investment_detail.price_action_levels

    if levels:
        cards = []
        for level in levels:
            cards.append(
                f"""
                <div class="price-action-card">
                  <div class="pa-label">{_esc(level.label)}</div>
                  <div class="pa-price">{_mono(level.price_range)}</div>
                  <div class="pa-rationale">{_esc(level.rationale)}</div>
                </div>
                """
            )
        return f'<div class="price-action-grid">{"".join(cards)}</div>'

    return f"""
    <div class="price-action-grid">
      <div class="price-action-card buy-zone">
        <div class="pa-label">建議買入價位 Buy Zone</div>
        <div class="pa-price">{_mono(report.suggested_buy_price)}</div>
      </div>
      <div class="price-action-card profit-zone">
        <div class="pa-label">止盈 / 放貨價位 Take Profit</div>
        <div class="pa-price">{_mono(report.take_profit_price)}</div>
      </div>
      <div class="price-action-card target-zone">
        <div class="pa-label">目標價區間 Target Range</div>
        <div class="pa-price">{_mono(report.target_price_range)}</div>
      </div>
      <div class="price-action-card stop-zone">
        <div class="pa-label">止蝕價位 Stop Loss</div>
        <div class="pa-price">{_mono(report.stop_loss_price or "視風險承受能力設定")}</div>
      </div>
    </div>
    """


def _build_conditions_block(title: str, content: str, css_class: str) -> str:
    lines = [line.strip(" •-\t") for line in re.split(r"[\n;]+", content or "") if line.strip()]
    if not lines:
        lines = [content or "—"]
    items = "".join(f"<li>{_esc(line)}</li>" for line in lines)
    return f"""
    <div class="condition-card {css_class}">
      <h4>{_esc(title)}</h4>
      <ul>{items}</ul>
    </div>
    """


def build_html_report(
    report: FundamentalReport,
    stock_info: StockInfo,
    financials: Financials,
) -> str:
    """Build a self-contained dark-theme HTML report from structured analysis data."""
    view_color = _view_color(report.overall_view)
    earnings_rows = report.earnings_table or _fallback_earnings_rows(financials)
    earnings_html = _build_earnings_table(earnings_rows)
    kpi_html = _build_kpi_cards(report.key_kpis)
    segment_html = _build_segment_cards(report.segment_breakdown, report.segment_performance)
    guidance_html = _build_guidance_table(report.guidance_comparison, report.guidance_vs_expectations)
    risk_html = _build_risk_cards(report.risk_factors_detail)
    price_action_html = _build_price_action_panel(report)

    price = stock_info.current_price
    market_cap = _format_large_number(float(stock_info.market_cap)) if stock_info.market_cap else "數據不可用"
    pe = stock_info.pe_ratio if stock_info.pe_ratio is not None else "數據不可用"
    currency = stock_info.currency or "USD"

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{_esc(report.company_name)} ({_esc(report.ticker)}) 基本面分析報告</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; padding: 28px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", sans-serif;
      background: {DARK_BG}; color: {TEXT_PRIMARY}; line-height: 1.7;
    }}
    .container {{ max-width: 1180px; margin: 0 auto; }}
    .header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border: 1px solid {BORDER}; border-radius: 18px;
      padding: 30px 34px; margin-bottom: 24px;
    }}
    .header h1 {{ margin: 0 0 10px; font-size: 2rem; letter-spacing: -0.02em; }}
    .header .meta {{ color: {TEXT_MUTED}; font-size: 0.95rem; }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
    .badge {{
      background: {CARD_BG}; border: 1px solid {BORDER};
      border-radius: 999px; padding: 7px 14px; font-size: 0.84rem;
    }}
    .view-badge {{
      background: {view_color}22; color: {view_color};
      border: 1px solid {view_color}; border-radius: 999px;
      padding: 7px 14px; font-weight: 700;
    }}
    .section {{
      background: {CARD_BG}; border: 1px solid {BORDER};
      border-radius: 16px; padding: 24px 26px; margin-bottom: 22px;
    }}
    .section h2 {{
      margin: 0 0 18px; font-size: 1.25rem; color: #e2e8f0;
      border-bottom: 1px solid {BORDER}; padding-bottom: 12px;
    }}
    .section h3 {{ margin: 20px 0 12px; color: #cbd5e1; font-size: 1.02rem; }}
    .section h4 {{ margin: 0 0 8px; color: #e2e8f0; font-size: 0.98rem; }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      color: #7dd3fc; font-weight: 600;
    }}
    .muted {{ color: {TEXT_MUTED}; }}
    .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; margin-top: 12px; }}
    .data-table th, .data-table td {{
      border: 1px solid {BORDER}; padding: 12px 14px;
      text-align: left; vertical-align: top;
    }}
    .data-table th {{ background: #111827; color: #cbd5e1; font-weight: 600; }}
    .row-period {{ color: #64748b; font-size: 0.76rem; margin-top: 4px; }}
    .row-comment {{ color: {TEXT_MUTED}; font-size: 0.82rem; margin-top: 8px; line-height: 1.55; }}
    .positive {{ color: {GREEN}; font-weight: 700; }}
    .negative {{ color: {RED}; font-weight: 700; }}
    .inline {{ color: {YELLOW}; font-weight: 700; }}
    .na {{ color: {TEXT_MUTED}; }}
    .kpi-grid {{
      display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px;
    }}
    .kpi-card {{
      background: #111827; border: 1px solid {BORDER}; border-radius: 14px; padding: 16px;
      position: relative;
    }}
    .kpi-index {{
      position: absolute; top: 12px; right: 12px; color: #64748b; font-size: 0.75rem; font-weight: 700;
    }}
    .kpi-name {{ color: {TEXT_MUTED}; font-size: 0.84rem; margin-bottom: 8px; padding-right: 28px; }}
    .kpi-value {{ font-size: 1.15rem; font-weight: 700; margin-bottom: 8px; }}
    .kpi-assessment {{ color: #cbd5e1; font-size: 0.88rem; line-height: 1.5; }}
    .segment-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    .segment-card {{
      background: #111827; border: 1px solid {BORDER}; border-radius: 14px; padding: 16px;
    }}
    .risk-card {{
      background: linear-gradient(180deg, #2a1215 0%, #1f1012 100%);
      border: 1px solid #7f1d1d; border-left: 5px solid {RED};
      border-radius: 14px; padding: 18px; margin-bottom: 14px;
    }}
    .risk-header {{
      display: flex; justify-content: space-between; align-items: flex-start;
      gap: 12px; margin-bottom: 10px;
    }}
    .risk-header h4 {{ margin: 0; color: #fecaca; flex: 1; }}
    .impact-badge {{
      border-radius: 999px; padding: 5px 12px; font-size: 0.78rem; font-weight: 700; white-space: nowrap;
    }}
    .risk-body .label {{
      display: block; color: #fca5a5; font-size: 0.78rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px;
    }}
    .invest-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin: 16px 0;
    }}
    .invest-card {{
      background: #111827; border: 1px solid {BORDER}; border-radius: 14px; padding: 16px;
    }}
    .invest-card .label {{ color: {TEXT_MUTED}; font-size: 0.8rem; margin-bottom: 8px; }}
    .invest-card .value {{ color: #f8fafc; line-height: 1.55; }}
    .price-highlight {{
      background: #0b1220; border: 1px solid #1d4ed8; border-radius: 14px;
      padding: 18px; margin: 16px 0;
    }}
    .price-action-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin: 18px 0;
    }}
    .price-action-card {{
      background: #111827; border: 1px solid {BORDER}; border-radius: 14px; padding: 18px;
    }}
    .price-action-card.buy-zone {{ border-color: #166534; background: #0f1f15; }}
    .price-action-card.profit-zone {{ border-color: #1d4ed8; background: #0b1220; }}
    .price-action-card.target-zone {{ border-color: #7c3aed; background: #151027; }}
    .price-action-card.stop-zone {{ border-color: #991b1b; background: #1f1012; }}
    .pa-label {{ color: {TEXT_MUTED}; font-size: 0.8rem; margin-bottom: 8px; font-weight: 600; }}
    .pa-price {{ font-size: 1.35rem; font-weight: 800; margin-bottom: 10px; }}
    .pa-rationale {{ color: #cbd5e1; font-size: 0.86rem; line-height: 1.5; }}
    .conditions-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 16px;
    }}
    .condition-card {{
      border-radius: 14px; padding: 16px; border: 1px solid {BORDER}; background: #111827;
    }}
    .condition-card.buy {{ border-color: #166534; }}
    .condition-card.hold {{ border-color: #854d0e; }}
    .condition-card.sell {{ border-color: #991b1b; }}
    .condition-card ul {{ margin: 0; padding-left: 18px; color: #dbe4f0; }}
    .condition-card li {{ margin-bottom: 8px; }}
    .section-note {{ margin-top: 14px; }}
    .footer-note {{
      background: #111827; border: 1px dashed {BORDER}; border-radius: 14px;
      padding: 18px; color: {TEXT_MUTED}; font-size: 0.92rem;
    }}
    p {{ margin: 0 0 12px; color: #dbe4f0; }}
  </style>
</head>
<body>
  <div class="container">
    <header class="header">
      <h1>{_esc(report.company_name)} <span class="mono">({_esc(report.ticker)})</span></h1>
      <div class="meta">
        專業基本面分析報告 ｜ 分析日期：{_esc(report.analysis_date)} ｜ 數據更新時間：{_esc(report.data_updated_at)}
      </div>
      <div class="badge-row">
        <span class="badge">最新股價：{_mono(f"{price} {currency}" if price else "數據不可用")}</span>
        <span class="badge">市值：{_mono(market_cap)}</span>
        <span class="badge">PE：{_mono(pe)}</span>
        <span class="view-badge">整體看法：{_esc(report.overall_view)}</span>
        <span class="badge">建議：{_esc(report.recommendation)}</span>
        <span class="badge">信心：{_esc(report.confidence)}</span>
      </div>
    </header>

    <section class="section">
      <h2>📋 執行摘要 Executive Summary</h2>
      {_paragraphs(report.executive_summary)}
    </section>

    <section class="section">
      <h2>📊 最新財報摘要 Latest Earnings Summary</h2>
      <p class="muted">{_esc(report.earnings_summary)}</p>
      <table class="data-table">
        <thead>
          <tr>
            <th>項目 (English / 繁體中文)</th>
            <th>實際數字 Actual</th>
            <th>市場預期 Consensus</th>
            <th>YoY 增長</th>
            <th>結果 Result</th>
          </tr>
        </thead>
        <tbody>{earnings_html}</tbody>
      </table>
    </section>

    <section class="section">
      <h2>🎯 關鍵 KPI 一覽 Key KPIs</h2>
      {kpi_html}
    </section>

    <section class="section">
      <h2>🏢 業務分部表現詳情 Segment Performance</h2>
      {segment_html}
      <h3>綜合業務分析</h3>
      {_paragraphs(report.segment_performance)}
    </section>

    <section class="section">
      <h2>🔮 前瞻指引與市場預期對比 Guidance vs Expectations</h2>
      {guidance_html}
    </section>

    <section class="section">
      <h2>💰 財務與估值分析 Financial & Valuation</h2>
      <h3>財務分析</h3>
      {_paragraphs(report.financial_analysis)}
      <h3>估值評估</h3>
      {_paragraphs(report.valuation_assessment)}
      <h3>競爭護城河</h3>
      {_paragraphs(report.competitive_moat)}
    </section>

    <section class="section">
      <h2>⚠️ 主要風險因素 Key Risks</h2>
      {risk_html}
    </section>

    <section class="section">
      <h2>💡 投資總結與建議 Investment Summary</h2>
      <div class="badge-row" style="margin-bottom:16px;">
        <span class="view-badge">整體看法：{_esc(report.overall_view)}</span>
        <span class="badge">操作建議：{_esc(report.recommendation)}</span>
        <span class="badge">信心水平：{_esc(report.confidence)}</span>
      </div>
      <h3>核心價位操作區間 Price Action Levels</h3>
      {price_action_html}
      <div class="invest-grid">
        <div class="invest-card">
          <div class="label">短期展望（1-3個月）</div>
          <div class="value">{_esc(report.short_term_outlook)}</div>
        </div>
        <div class="invest-card">
          <div class="label">中長期展望（6-12個月）</div>
          <div class="value">{_esc(report.medium_long_term_outlook)}</div>
        </div>
        <div class="invest-card">
          <div class="label">目前股價分析</div>
          <div class="value">{_esc(report.current_price_analysis)}</div>
        </div>
      </div>
      <div class="price-highlight">
        <h3>目標價理由 Target Price Rationale</h3>
        {_paragraphs(report.target_price_rationale)}
      </div>
      <h3>整體投資策略 Investment Strategy</h3>
      {_paragraphs(report.investment_strategy)}
      <h3>投資展望 Investment Outlook</h3>
      {_paragraphs(report.investment_outlook)}
      <div class="conditions-grid">
        {_build_conditions_block("買入條件 Buy Conditions", report.buy_conditions, "buy")}
        {_build_conditions_block("持有條件 Hold Conditions", report.hold_conditions, "hold")}
        {_build_conditions_block("賣出條件 Sell Conditions", report.sell_conditions, "sell")}
      </div>
    </section>

    <section class="section footer-note">
      <strong>✅ 數據時效確認</strong><br /><br />
      <strong>本次分析所有數據嘅最新更新時間：</strong>{_esc(report.data_updated_at)}<br />
      <strong>即時數據使用情況：</strong>{_esc(report.realtime_data_note)}
    </section>
  </div>
</body>
</html>"""