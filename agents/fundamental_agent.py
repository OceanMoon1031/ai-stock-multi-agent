"""Fundamental analysis agent powered by xAI Grok."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from agents.html_report import build_html_report
from agents.models import FundamentalReport, InvestmentSummaryDetail
from tools import get_financials, get_stock_info
from tools.models import Financials, StockInfo
from utils.config import ConfigurationError, get_grok_client, get_settings

HKT = ZoneInfo("Asia/Hong_Kong")

SYSTEM_PROMPT = """你是一位擁有15年以上經驗的專業股票分析師，專精於科技股與AI基礎設施領域。

【Chain-of-Thought 要求 — 必須遵守】
在輸出最終 JSON 之前，你必須先在內部完整思考：
1) 核對所有最新股價、財報、現金流、估值數據；
2) 逐項分析 8 大維度（股價估值、財報質量、KPI、分部、指引、護城河、風險、投資策略）；
3) 為每個風險同投資價位建立清晰邏輯鏈。
⚠️ 思考過程只在內部進行，最終只輸出 JSON，不要輸出思考步驟。

【最重要提醒 — 必須嚴格遵守】
1. 使用即時最新數據；絕不以舊數據冒充最新。
2. 所有分析標註數據更新時間（HKT）。
3. 內容必須是「詳細分析式」，唔可以只做高層總結。
4. 香港投資者視角，繁體中文，直接實用，專業客觀。

【數據誠信】
- 只能使用用戶提供 stock data；禁止虛構數字。
- 無 consensus 數據時：consensus =「數據不可用」，result =「N/A」，commentary 必須解釋。
- 不可憑空猜測 Beat/Miss 或市場預期。

【必須嚴格遵守 — 詳細內容最低標準】

★ earnings_table（必須 8 行，完整雙語表格）
  必須包含：Revenue（營收）、Gross Profit（毛利）、Operating Income（營業利潤）、
  GAAP Net Income（GAAP 淨利潤）、Non-GAAP EPS、Free Cash Flow（自由現金流）、
  Gross Margin（毛利率）、R&D Expense（研發費用）。
  每行必須有：metric, period, actual, consensus, yoy_growth, result, commentary（2-3句分析）。
  commentary 必須解釋趨勢、同比變化、對投資者意義，唔可以只寫一句空話。

★ key_kpis（必須 7-9 項）
  每項：name（雙語）、value、assessment（2-3句有意義評價，含投資含義）。

★ risk_factors_detail（必須 6-7 項，每項必須詳細）
  - title：清晰風險名稱
  - description：至少 3 句，解釋風險機制、成因、現況
  - potential_impact：至少 2 句，具體說明對營收/毛利/估值/股價影響
  - impact_level：高/中高/中/中低/低
  - monitoring_signal：投資者應監察嘅預警信號

★ investment_detail（必須極其詳細，唔可以含糊）
  - overall_view：Bullish/Neutral/Bearish
  - short_term_outlook：1-3個月，至少 5 句詳細分析
  - medium_long_term_outlook：6-12個月，至少 5 句
  - current_price_analysis：至少 5 句，必須引用最新股價、PE、52週高低
  - suggested_buy_price：必須為具體數字區間（例如 180-195 USD）
  - take_profit_price：必須為具體數字區間（例如 250-270 USD）
  - target_price_range：必須為具體數字區間（例如 250-280 USD）
  - stop_loss_price：建議止蝕區間（如有）
  - target_price_rationale：至少 6 句，引用估值/成長/同業對比
  - buy_conditions：至少 4 個具體買入條件（可含價位、技術、財報催化劑）
  - hold_conditions：至少 3 個具體持有條件
  - sell_conditions：至少 3 個具體賣出條件
  - investment_strategy：至少 10 句，說明分批買入、倉位管理、事件驅動應對
  - price_action_levels：至少 3 項（買入區/止盈區/目標區），每項含 label, price_range, rationale
  - recommendation, confidence

★ 其他敘述欄位最低要求
  - executive_summary：10-15 句
  - financial_analysis：12+ 句，含多期趨勢
  - earnings_summary：6+ 句
  - segment_performance：8+ 句
  - guidance_vs_expectations：8+ 句

【輸出格式】只返回有效 JSON，無 markdown fence，無額外文字。"""

JSON_SCHEMA_HINT = """
{
  "ticker": "string",
  "company_name": "string",
  "analysis_date": "string",
  "data_updated_at": "string",
  "realtime_data_note": "string",
  "executive_summary": "string (10-15 sentences)",
  "business_overview": "string (8-12 sentences)",
  "financial_analysis": "string (12+ sentences)",
  "earnings_summary": "string (6+ sentences)",
  "earnings_table": [
    {
      "metric": "Revenue（營收）",
      "period": "FY2025",
      "actual": "string",
      "consensus": "string or 數據不可用",
      "yoy_growth": "+12.3%",
      "result": "Beat|Miss|Inline|N/A",
      "commentary": "string (2-3 sentences)"
    }
  ],
  "key_kpis": [{"name": "P/E Ratio（市盈率）", "value": "string", "assessment": "string (2-3 sentences)"}],
  "segment_breakdown": [{"segment_name": "string", "performance_summary": "string", "ai_relevance": "string", "growth_outlook": "string"}],
  "segment_performance": "string (8+ sentences)",
  "guidance_comparison": [{"metric": "string", "company_guidance": "string", "market_expectation": "string", "gap_analysis": "string"}],
  "guidance_vs_expectations": "string (8+ sentences)",
  "valuation_assessment": "string (8+ sentences)",
  "competitive_moat": "string (6+ sentences)",
  "risk_factors_detail": [
    {
      "title": "string",
      "description": "string (3+ sentences)",
      "potential_impact": "string (2+ sentences)",
      "impact_level": "高|中高|中|中低|低",
      "monitoring_signal": "string"
    }
  ],
  "risk_factors": ["string"],
  "investment_detail": {
    "overall_view": "Bullish|Neutral|Bearish",
    "short_term_outlook": "string (5+ sentences)",
    "medium_long_term_outlook": "string (5+ sentences)",
    "current_price_analysis": "string (5+ sentences)",
    "suggested_buy_price": "180-195 USD",
    "take_profit_price": "250-270 USD",
    "target_price_range": "250-280 USD",
    "stop_loss_price": "string",
    "target_price_rationale": "string (6+ sentences)",
    "buy_conditions": "string (4+ bullet points)",
    "hold_conditions": "string (3+ bullet points)",
    "sell_conditions": "string (3+ bullet points)",
    "investment_strategy": "string (10+ sentences)",
    "price_action_levels": [
      {"label": "建議買入區間", "price_range": "180-195 USD", "rationale": "string"}
    ],
    "recommendation": "Strong Buy|Buy|Hold|Sell|Strong Sell",
    "confidence": "High|Medium|Low"
  },
  "overall_view": "Bullish|Neutral|Bearish",
  "short_term_outlook": "string",
  "medium_long_term_outlook": "string",
  "current_price_analysis": "string",
  "suggested_buy_price": "string",
  "take_profit_price": "string",
  "target_price_range": "string",
  "target_price_rationale": "string",
  "stop_loss_price": "string",
  "buy_conditions": "string",
  "hold_conditions": "string",
  "sell_conditions": "string",
  "investment_strategy": "string",
  "investment_outlook": "string",
  "price_action_levels": [{"label": "string", "price_range": "string", "rationale": "string"}],
  "recommendation": "Strong Buy|Buy|Hold|Sell|Strong Sell",
  "confidence": "High|Medium|Low",
  "report_markdown": "string (extremely detailed)"
}"""


class FundamentalReportAgent:
    """Agent that generates a fundamental analysis report for a given ticker."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or get_settings().xai_model

    def run(self, ticker: str) -> FundamentalReport:
        """Fetch stock data and generate a fundamental analysis report."""
        symbol = ticker.strip().upper()
        if not symbol:
            raise ValueError("Ticker symbol cannot be empty.")

        stock_info = get_stock_info(symbol)
        financials = get_financials(symbol)
        prompt = self._build_prompt(stock_info, financials)
        raw_response = self._call_grok(prompt)
        report = self._parse_report(raw_response, symbol, stock_info.name or symbol)
        html_report = build_html_report(report, stock_info, financials)
        return report.model_copy(update={"html_report": html_report})

    @staticmethod
    def _now_hkt() -> datetime:
        return datetime.now(HKT)

    def _build_prompt(self, stock_info: StockInfo, financials: Financials) -> str:
        """Compose the user prompt with structured stock data."""
        now = self._now_hkt()
        analysis_date = now.strftime("%Y年%m月%d日")
        data_updated_at = now.strftime("截至%Y年%m月%d日 %H:%M HKT")

        payload: dict[str, Any] = {
            "data_snapshot_time_hkt": data_updated_at,
            "stock_info": stock_info.model_dump(),
            "financials": financials.model_dump(),
        }
        data_json = json.dumps(payload, indent=2, ensure_ascii=False)

        return f"""請為以下股票生成一份「詳細分析式」基本面報告（質素必須接近用戶 Step 1 手動 prompt 水準）。

⚠️ 請先內部思考所有數據同分析邏輯，然後只輸出 JSON。

股票代碼：{stock_info.ticker}
股票全名：{stock_info.name}
分析日期：{analysis_date}
數據更新時間：{data_updated_at}
行業：{stock_info.sector or "Data not available"} / {stock_info.industry or "Data not available"}
最新股價：{stock_info.current_price or "Data not available"} {stock_info.currency or ""}
52週高/低：{stock_info.fifty_two_week_high or "N/A"} / {stock_info.fifty_two_week_low or "N/A"}
市值：{stock_info.market_cap or "Data not available"}
市盈率 (PE)：{stock_info.pe_ratio or "Data not available"}
Forward PE：{stock_info.forward_pe or "Data not available"}
EPS：{stock_info.eps or "Data not available"}
Beta：{stock_info.beta or "Data not available"}

=== 供應商數據 (JSON) ===
{data_json}

=== 嚴格輸出要求（違反視為失敗）===
- earnings_table 必須 8 行完整雙語表格，commentary 每行 2-3 句。
- key_kpis 必須 7-9 項，assessment 每項 2-3 句。
- risk_factors_detail 必須 6-7 項，description 至少 3 句，potential_impact 至少 2 句，必須有 monitoring_signal。
- investment_detail 必須包含具體數字價位區間（買入/止盈/目標/止蝕），策略至少 10 句。
- 禁止輸出空泛總結；必須引用具體數字同邏輯。
- 同步填入 investment_detail 及頂層欄位。

JSON schema:
{JSON_SCHEMA_HINT}

只返回 JSON。"""

    def _call_grok(self, prompt: str) -> str:
        """Call the Grok API and return the raw text response."""
        try:
            client = get_grok_client()
        except ConfigurationError:
            raise

        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.33,
                max_tokens=16000,
            )
        except Exception as exc:
            raise RuntimeError(f"Grok API call failed: {exc}") from exc

        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("Grok API returned an empty response.")
        return content

    @staticmethod
    def _normalize_text_field(value: Any) -> str:
        """Coerce LLM list outputs into display-friendly strings."""
        if value is None:
            return ""
        if isinstance(value, list):
            return "\n".join(f"• {str(item).strip()}" for item in value if str(item).strip())
        return str(value).strip()

    @classmethod
    def _normalize_detail_dict(cls, detail: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(detail)
        text_keys = (
            "buy_conditions",
            "hold_conditions",
            "sell_conditions",
            "investment_strategy",
            "target_price_rationale",
            "short_term_outlook",
            "medium_long_term_outlook",
            "current_price_analysis",
        )
        for key in text_keys:
            if key in normalized:
                normalized[key] = cls._normalize_text_field(normalized[key])
        return normalized

    @classmethod
    def _normalize_risks(cls, risks: Any) -> list[dict[str, Any]]:
        if not isinstance(risks, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in risks:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            for key in ("description", "potential_impact", "monitoring_signal", "title"):
                if key in row:
                    row[key] = cls._normalize_text_field(row[key])
            normalized.append(row)
        return normalized

    @classmethod
    def _sync_investment_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Flatten investment_detail into top-level fields for model compatibility."""
        detail = data.get("investment_detail")
        if not isinstance(detail, dict):
            return data

        inv = InvestmentSummaryDetail.model_validate(cls._normalize_detail_dict(detail))
        data.update(
            {
                "overall_view": inv.overall_view,
                "short_term_outlook": inv.short_term_outlook,
                "medium_long_term_outlook": inv.medium_long_term_outlook,
                "current_price_analysis": inv.current_price_analysis,
                "suggested_buy_price": inv.suggested_buy_price,
                "take_profit_price": inv.take_profit_price,
                "target_price_range": inv.target_price_range,
                "target_price_rationale": inv.target_price_rationale,
                "stop_loss_price": inv.stop_loss_price,
                "buy_conditions": inv.buy_conditions,
                "hold_conditions": inv.hold_conditions,
                "sell_conditions": inv.sell_conditions,
                "investment_strategy": inv.investment_strategy,
                "price_action_levels": [level.model_dump() for level in inv.price_action_levels],
                "recommendation": inv.recommendation,
                "confidence": inv.confidence,
            }
        )
        data["investment_detail"] = inv.model_dump()
        return data

    def _parse_report(
        self,
        raw_response: str,
        ticker: str,
        company_name: str,
    ) -> FundamentalReport:
        """Parse and validate the Grok JSON response into a FundamentalReport."""
        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse Grok response as JSON: {exc}") from exc

        data.pop("analysis_scratchpad", None)

        now = self._now_hkt()
        data.setdefault("ticker", ticker)
        data.setdefault("company_name", company_name)
        data.setdefault("analysis_date", now.strftime("%Y年%m月%d日"))
        data.setdefault("data_updated_at", now.strftime("截至%Y年%m月%d日 %H:%M HKT"))

        if "risk_factors_detail" in data:
            data["risk_factors_detail"] = self._normalize_risks(data["risk_factors_detail"])

        data = self._sync_investment_fields(data)
        for key in (
            "buy_conditions",
            "hold_conditions",
            "sell_conditions",
            "investment_strategy",
            "target_price_rationale",
            "investment_outlook",
        ):
            if key in data:
                data[key] = self._normalize_text_field(data[key])

        return FundamentalReport.model_validate(data)