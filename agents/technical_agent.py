"""Technical analysis agent (Step 3) powered by xAI Grok."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from agents.models import TechnicalAnalysisReport
from tools import calculate_technical_indicators, get_financials, get_stock_info
from tools.models import Financials, StockInfo, TechnicalIndicatorSnapshot
from utils.config import ConfigurationError, get_grok_client, get_settings

HKT = ZoneInfo("Asia/Hong_Kong")

SECTION_SPECS: list[tuple[int, str, str]] = [
    (1, "overall_summary", "1. 整體技術面總結"),
    (2, "key_indicators_analysis", "2. 關鍵技術指標分析"),
    (3, "chart_patterns_and_levels", "3. 圖表形態與關鍵位置"),
    (4, "technical_conclusion", "4. 技術面總結判斷"),
    (5, "entry_strategy", "5. 入場策略建議"),
    (6, "risk_warnings", "6. 風險提示"),
]

FIELD_BY_SECTION = {spec[0]: spec[1] for spec in SECTION_SPECS}

SYSTEM_PROMPT = """你是一位擁有15年以上經驗、極度專業嘅技術分析師，專精於美股科技股同AI相關股票。

【最重要提醒 — 必須嚴格遵守】
* 你必須使用即時最新數據（盡量用今天最新走勢，包括盤中最新價格同技術指標）。
* 絕對唔可以用昨日或更早嘅資料冒充最新。
* 所有分析都要明確標註「數據更新時間」。
* 如果冇辦法取得即時數據，必須明確講出嚟，並盡量用最新可用數據。

【任務】
請對股票進行詳細技術面分析，並直接給出入場策略建議。
必須優先使用用戶提供嘅 technical_indicators 計算數據（RSI、MACD、MA 等），禁止虛構指標數值。

【必須完整輸出 6 個 Section】
1. 整體技術面總結（詳細）
2. 關鍵技術指標分析（RSI、MACD、MA、成交量等，必須詳細）
3. 圖表形態與關鍵位置（支撐/阻力、52週高低）
4. 技術面總結判斷
5. 入場策略建議（具體價位、分批方式）
6. 風險提示

【策略欄位 — 必須具體】
- technical_rating：強烈看多/看多/中性/看空/強烈看空
- suitable_for_entry：是/否/觀望
- entry_price_range、stop_loss、take_profit_1、take_profit_2、position_size（具體數字區間）

【輸出格式】只返回有效 JSON，無 markdown fence，無額外文字。"""

JSON_SCHEMA_HINT = """
{
  "ticker": "string",
  "company_name": "string",
  "analysis_date": "string",
  "data_updated_at": "string",
  "realtime_data_note": "string",
  "sections": [
    {"section_id": 1, "title": "整體技術面總結", "analysis": "string", "key_points": ["string"]}
  ],
  "overall_summary": "string",
  "key_indicators_analysis": "string",
  "chart_patterns_and_levels": "string",
  "technical_conclusion": "string",
  "entry_strategy": "string",
  "risk_warnings": "string",
  "technical_rating": "強烈看多|看多|中性|看空|強烈看空",
  "suitable_for_entry": "是|否|觀望",
  "entry_price_range": "string",
  "stop_loss": "string",
  "take_profit_1": "string",
  "take_profit_2": "string",
  "position_size": "string",
  "report_markdown": "string"
}"""


class TechnicalAnalysisAgent:
    """Agent that performs Step 3 technical analysis."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or get_settings().xai_model

    def run(self, ticker: str) -> TechnicalAnalysisReport:
        symbol = ticker.strip().upper()
        if not symbol:
            raise ValueError("Ticker symbol cannot be empty.")

        stock_info = get_stock_info(symbol)
        financials = get_financials(symbol)
        indicators = calculate_technical_indicators(symbol)
        prompt = self._build_prompt(stock_info, financials, indicators)
        raw_response = self._call_grok(prompt)
        return self._parse_report(raw_response, symbol, stock_info.name or symbol)

    @staticmethod
    def _now_hkt() -> datetime:
        return datetime.now(HKT)

    def _build_prompt(
        self,
        stock_info: StockInfo,
        financials: Financials,
        indicators: TechnicalIndicatorSnapshot,
    ) -> str:
        now = self._now_hkt()
        analysis_date = now.strftime("%Y年%m月%d日")
        data_updated_at = now.strftime("截至%Y年%m月%d日 %H:%M HKT")

        payload: dict[str, Any] = {
            "data_snapshot_time_hkt": data_updated_at,
            "stock_info": stock_info.model_dump(),
            "financials": financials.model_dump(),
            "technical_indicators": indicators.model_dump(),
        }
        data_json = json.dumps(payload, indent=2, ensure_ascii=False)

        return f"""請對以下股票進行 Step 3 技術面分析，並給出入場策略。

股票代碼：{stock_info.ticker}
股票全名：{stock_info.name}
分析日期：{analysis_date}
數據更新時間：{data_updated_at}

⚠️ 必須使用 technical_indicators 入面已計算嘅 RSI、MACD、SMA 數據，不可虛構。

=== 供應商數據 (JSON) ===
{data_json}

=== 輸出要求 ===
- 完整 6 個 section，每項詳細分析
- sections 陣列包含 section_id 1-6
- 同時填寫 6 個頂層欄位
- 入場策略必須包含具體價位
- 最後 realtime_data_note 確認數據時效

JSON schema:
{JSON_SCHEMA_HINT}

只返回 JSON。"""

    def _call_grok(self, prompt: str) -> str:
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
                temperature=0.28,
                max_tokens=12000,
            )
        except Exception as exc:
            raise RuntimeError(f"Grok API call failed: {exc}") from exc

        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("Grok API returned an empty response.")
        return content

    @classmethod
    def _merge_sections_into_fields(cls, data: dict[str, Any]) -> None:
        sections = data.get("sections")
        if not isinstance(sections, list):
            return
        for item in sections:
            if not isinstance(item, dict):
                continue
            section_id = item.get("section_id")
            field_name = FIELD_BY_SECTION.get(section_id)
            if not field_name:
                continue
            analysis = str(item.get("analysis", "")).strip()
            if analysis and len(str(data.get(field_name, "")).strip()) < len(analysis):
                data[field_name] = analysis

    @classmethod
    def _compose_report_markdown(cls, report: TechnicalAnalysisReport) -> str:
        field_values = {
            "overall_summary": report.overall_summary,
            "key_indicators_analysis": report.key_indicators_analysis,
            "chart_patterns_and_levels": report.chart_patterns_and_levels,
            "technical_conclusion": report.technical_conclusion,
            "entry_strategy": report.entry_strategy,
            "risk_warnings": report.risk_warnings,
        }
        section_by_id = {section.section_id: section for section in report.sections}

        lines = [
            f"# {report.company_name} ({report.ticker}) 技術面分析報告",
            "",
            f"**分析日期**：{report.analysis_date}  ",
            f"**數據更新時間**：{report.data_updated_at}  ",
            f"**技術面評級**：{report.technical_rating}  ",
            f"**是否適合入場**：{report.suitable_for_entry}  ",
            "",
        ]

        for section_id, field_name, title in SECTION_SPECS:
            content = field_values.get(field_name, "").strip()
            if not content:
                section = section_by_id.get(section_id)
                content = section.analysis if section else "（內容缺失）"
            lines.extend([f"## {title}", "", content, ""])
            section = section_by_id.get(section_id)
            if section and section.key_points:
                lines.append("**要點：**")
                lines.extend(f"- {point}" for point in section.key_points)
                lines.append("")

        lines.extend(
            [
                "## 入場策略摘要",
                "",
                f"- **入場價區間**：{report.entry_price_range}",
                f"- **止蝕位**：{report.stop_loss}",
                f"- **止盈目標 1**：{report.take_profit_1}",
                f"- **止盈目標 2**：{report.take_profit_2}",
                f"- **建議倉位**：{report.position_size}",
                "",
                "## 數據時效確認",
                "",
                report.realtime_data_note,
            ]
        )
        return "\n".join(lines)

    def _parse_report(
        self,
        raw_response: str,
        ticker: str,
        company_name: str,
    ) -> TechnicalAnalysisReport:
        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse Grok response as JSON: {exc}") from exc

        now = self._now_hkt()
        data.setdefault("ticker", ticker)
        data.setdefault("company_name", company_name)
        data.setdefault("analysis_date", now.strftime("%Y年%m月%d日"))
        data.setdefault("data_updated_at", now.strftime("截至%Y年%m月%d日 %H:%M HKT"))

        self._merge_sections_into_fields(data)

        report = TechnicalAnalysisReport.model_validate(data)
        markdown = self._compose_report_markdown(report)
        return report.model_copy(update={"report_markdown": markdown})