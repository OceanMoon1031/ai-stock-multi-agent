"""Deep pre-buy check agent (Step 2) powered by xAI Grok."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from agents.models import DeepCheckReport, DeepCheckUserProfile
from tools import get_financials, get_stock_info
from tools.models import Financials, StockInfo
from utils.config import ConfigurationError, get_grok_client, get_settings

HKT = ZoneInfo("Asia/Hong_Kong")
MAX_ATTEMPTS = 3
MIN_DIMENSION_CHARS = 120

DIMENSION_SPECS: list[tuple[int, str, str]] = [
    (1, "management_quality", "Section 1：管理層質素 + 執行力"),
    (2, "moat_and_ai_leadership", "Section 2：真正嘅護城河（Moat）同 AI 真實領導力"),
    (3, "macro_geopolitics", "Section 3：宏觀 + 地緣政治環境"),
    (4, "market_sentiment", "Section 4：市場情緒 + 資金流向"),
    (5, "technical_timing", "Section 5：技術面 + 入市時機"),
    (6, "valuation_fairness", "Section 6：估值是否合理"),
    (7, "catalysts_and_black_swans", "Section 7：Catalysts 同黑天鵝風險"),
    (8, "personal_fit", "Section 8：個人情況匹配度"),
]

FIELD_BY_ID = {spec[0]: spec[1] for spec in DIMENSION_SPECS}

SYSTEM_PROMPT = """你是一位擁有15年以上經驗、極度嚴謹嘅專業股票分析師，專精於科技股同AI基礎設施領域。
你持強烈懷疑態度，永遠會交叉驗證所有資訊，唔會輕易相信單一來源。

【⚠️ 完整性強制要求 — 違反即失敗】
★ 你必須完整生成所有 8 個維度，絕對唔可以遺漏任何一個維度。
★ dimensions 陣列必須包含 dimension_id 1,2,3,4,5,6,7,8 共 8 項，缺一不可。
★ 同時必須填寫 management_quality、moat_and_ai_leadership、macro_geopolitics、
  market_sentiment、technical_timing、valuation_fairness、catalysts_and_black_swans、personal_fit
  共 8 個頂層欄位，內容與 dimensions 一致。
★ 每個維度 analysis 及對應頂層欄位必須至少 150–250 字詳細分析，唔可以只寫一兩句。
★ 特別強調以下維度必須詳細生成（不可省略或敷衍）：
  - Section 2：護城河（Moat）同 AI 真實領導力
  - Section 3：宏觀 + 地緣政治（香港投資者視角）
  - Section 6：估值是否合理
  - Section 7：Catalysts 與黑天鵝風險

【Chain-of-Thought — 必須遵守】
輸出 JSON 前，必須先在內部逐項完成 8 個維度分析，再輸出 JSON。
⚠️ 只輸出 JSON，不要輸出思考過程。

【8 個維度清單 — 必須全部輸出】
1. 管理層質素 + 執行力（最重要）
2. 真正嘅護城河（Moat）同 AI 真實領導力
3. 宏觀 + 地緣政治環境（香港人尤其要睇）
4. 市場情緒 + 資金流向
5. 技術面 + 入市時機
6. 估值是否合理
7. 即將到來嘅 catalysts 同黑天鵝風險
8. 個人情況匹配度（最重要）— 必須結合用戶個人資料

【最後總結 — 必須包含】
- overall_rating、suggested_position_size、entry_price_range、stop_loss
- main_buy_reasons（至少 3 點）、max_risk、final_recommendation（至少 6 句）
- realtime_data_note：是否已盡量使用即時最新數據

【數據誠信】只能使用用戶提供數據；禁止虛構；缺失必須標註。

【輸出格式】只返回有效 JSON，無 markdown fence，無額外文字。"""

JSON_SCHEMA_HINT = """
{
  "ticker": "string",
  "company_name": "string",
  "analysis_date": "string",
  "data_updated_at": "string",
  "realtime_data_note": "string",
  "dimensions": [
    {"dimension_id": 1, "title": "管理層質素 + 執行力", "analysis": "150-250字", "key_findings": [], "risk_flags": [], "verdict": "正面|中性|負面"},
    {"dimension_id": 2, "title": "護城河 + AI領導力", "analysis": "150-250字", "key_findings": [], "risk_flags": [], "verdict": "..."},
    {"dimension_id": 3, "title": "宏觀地緣政治", "analysis": "150-250字", ...},
    {"dimension_id": 4, ...},
    {"dimension_id": 5, ...},
    {"dimension_id": 6, ...},
    {"dimension_id": 7, ...},
    {"dimension_id": 8, ...}
  ],
  "management_quality": "Section 1 完整內容（150-250字）",
  "moat_and_ai_leadership": "Section 2 完整內容（150-250字）",
  "macro_geopolitics": "Section 3 完整內容（150-250字）",
  "market_sentiment": "Section 4 完整內容（150-250字）",
  "technical_timing": "Section 5 完整內容（150-250字）",
  "valuation_fairness": "Section 6 完整內容（150-250字）",
  "catalysts_and_black_swans": "Section 7 完整內容（150-250字）",
  "personal_fit": "Section 8 完整內容（150-250字）",
  "overall_rating": "Strong Buy|Buy|Neutral|Avoid",
  "suggested_position_size": "string",
  "entry_price_range": "string",
  "stop_loss": "string",
  "main_buy_reasons": ["string"],
  "max_risk": "string",
  "final_recommendation": "string",
  "report_markdown": "string (可簡短，系統會重組)"
}"""


class DeepCheckAgent:
    """Agent that performs Step 2 deep pre-buy due diligence."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or get_settings().xai_model

    def run(
        self,
        ticker: str,
        *,
        available_capital: str = "",
        risk_tolerance: str = "",
        investment_horizon: str = "",
        portfolio_concentration: str = "",
    ) -> DeepCheckReport:
        """Fetch data and generate a deep pre-buy check report."""
        symbol = ticker.strip().upper()
        if not symbol:
            raise ValueError("Ticker symbol cannot be empty.")

        user_profile = DeepCheckUserProfile(
            available_capital=available_capital,
            risk_tolerance=risk_tolerance,
            investment_horizon=investment_horizon,
            portfolio_concentration=portfolio_concentration,
        )

        stock_info = get_stock_info(symbol)
        financials = get_financials(symbol)
        base_prompt = self._build_prompt(stock_info, financials, user_profile)

        last_error: str | None = None
        missing_sections: list[str] = []

        for attempt in range(1, MAX_ATTEMPTS + 1):
            prompt = (
                base_prompt
                if attempt == 1
                else self._build_retry_prompt(base_prompt, missing_sections, attempt)
            )
            try:
                raw_response = self._call_grok(prompt)
                report = self._parse_report(
                    raw_response,
                    symbol,
                    stock_info.name or symbol,
                    user_profile,
                )
                missing_sections = self._find_missing_sections(report)
                if not missing_sections:
                    return report
                last_error = f"Incomplete report (attempt {attempt}): missing {missing_sections}"
            except (RuntimeError, ValueError) as exc:
                last_error = str(exc)

        raise RuntimeError(
            f"Deep check failed after {MAX_ATTEMPTS} attempts. "
            f"Last issue: {last_error}. Missing: {missing_sections}"
        )

    @staticmethod
    def _now_hkt() -> datetime:
        return datetime.now(HKT)

    def _build_prompt(
        self,
        stock_info: StockInfo,
        financials: Financials,
        user_profile: DeepCheckUserProfile,
    ) -> str:
        now = self._now_hkt()
        analysis_date = now.strftime("%Y年%m月%d日")
        data_updated_at = now.strftime("截至%Y年%m月%d日 %H:%M HKT")

        payload: dict[str, Any] = {
            "data_snapshot_time_hkt": data_updated_at,
            "stock_info": stock_info.model_dump(),
            "financials": financials.model_dump(),
            "user_profile": user_profile.model_dump(),
        }
        data_json = json.dumps(payload, indent=2, ensure_ascii=False)

        return f"""請對以下股票進行 Step 2「買之前 Deep Check」分析。

⚠️ 必須完整輸出全部 8 個維度（dimension_id 1-8），每項至少 150-250 字。

股票代碼：{stock_info.ticker}
股票全名：{stock_info.name}
分析日期：{analysis_date}
數據更新時間：{data_updated_at}

【用戶個人資料 — Section 8 必須使用】
- 可用資金：{user_profile.available_capital or "未提供"}
- 風險承受力：{user_profile.risk_tolerance or "未提供"}
- 投資期限：{user_profile.investment_horizon or "未提供"}
- 組合集中度：{user_profile.portfolio_concentration or "未提供"}

【最新市場快照】
- 股價：{stock_info.current_price or "N/A"} {stock_info.currency or ""}
- 52週高/低：{stock_info.fifty_two_week_high or "N/A"} / {stock_info.fifty_two_week_low or "N/A"}
- 市值：{stock_info.market_cap or "N/A"}
- PE / Forward PE：{stock_info.pe_ratio or "N/A"} / {stock_info.forward_pe or "N/A"}
- Beta：{stock_info.beta or "N/A"}

=== 供應商數據 (JSON) ===
{data_json}

=== 輸出檢查清單（全部必須完成）===
□ dimensions 包含 id 1,2,3,4,5,6,7,8
□ 8 個頂層欄位全部有 150-250 字內容
□ Section 2/3/6/7 特別詳細
□ 最後總結完整

JSON schema:
{JSON_SCHEMA_HINT}

只返回 JSON。"""

    @staticmethod
    def _build_retry_prompt(base_prompt: str, missing: list[str], attempt: int) -> str:
        missing_text = "、".join(missing)
        return f"""{base_prompt}

【⚠️ 重試第 {attempt} 次 — 上次輸出不完整】
缺失或內容過短嘅部分：{missing_text}

你必須重新生成完整 JSON：
1. 補齊所有缺失維度，絕對唔可以只輸出 Section 1 同 Section 8。
2. 每個維度至少 150-250 字。
3. dimensions 必須有 8 項（id 1-8）。
4. Section 2（護城河）、Section 3（地緣政治）、Section 6（估值）、Section 7（catalysts）必須詳細。

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
                max_tokens=20000,
            )
        except Exception as exc:
            raise RuntimeError(f"Grok API call failed: {exc}") from exc

        content = completion.choices[0].message.content
        finish_reason = completion.choices[0].finish_reason
        if finish_reason == "length":
            raise RuntimeError("Grok response truncated (max_tokens reached).")
        if not content:
            raise RuntimeError("Grok API returned an empty response.")
        return content

    @staticmethod
    def _normalize_text_field(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return "\n".join(f"• {str(item).strip()}" for item in value if str(item).strip())
        return str(value).strip()

    @staticmethod
    def _normalize_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            items = [line.strip(" •-\t") for line in value.split("\n") if line.strip()]
            return items or [value]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value)]

    @classmethod
    def _merge_dimensions_into_fields(cls, data: dict[str, Any]) -> None:
        """Sync dimensions[] into top-level section fields when missing or short."""
        dimensions = data.get("dimensions")
        if not isinstance(dimensions, list):
            return

        for item in dimensions:
            if not isinstance(item, dict):
                continue
            dim_id = item.get("dimension_id")
            field_name = FIELD_BY_ID.get(dim_id)
            if not field_name:
                continue
            analysis = cls._normalize_text_field(item.get("analysis", ""))
            if not analysis:
                continue
            existing = cls._normalize_text_field(data.get(field_name, ""))
            if len(existing) < len(analysis):
                data[field_name] = analysis

    @classmethod
    def _compose_report_markdown(cls, report: DeepCheckReport) -> str:
        """Rebuild markdown from structured sections to avoid LLM truncation."""
        lines = [
            f"# {report.company_name} ({report.ticker}) 深度買前檢查報告",
            "",
            f"**分析日期**：{report.analysis_date}  ",
            f"**數據更新時間**：{report.data_updated_at}  ",
            "",
        ]

        section_values = {
            "management_quality": report.management_quality,
            "moat_and_ai_leadership": report.moat_and_ai_leadership,
            "macro_geopolitics": report.macro_geopolitics,
            "market_sentiment": report.market_sentiment,
            "technical_timing": report.technical_timing,
            "valuation_fairness": report.valuation_fairness,
            "catalysts_and_black_swans": report.catalysts_and_black_swans,
            "personal_fit": report.personal_fit,
        }

        dim_by_id = {dim.dimension_id: dim for dim in report.dimensions}

        for dim_id, field_name, title in DIMENSION_SPECS:
            content = section_values.get(field_name, "").strip()
            if not content:
                dim = dim_by_id.get(dim_id)
                content = dim.analysis if dim else "（內容缺失）"

            lines.extend([f"## {title}", "", content, ""])
            dim = dim_by_id.get(dim_id)
            if dim and dim.key_findings:
                lines.append("**關鍵發現：**")
                lines.extend(f"- {finding}" for finding in dim.key_findings)
                lines.append("")
            if dim and dim.risk_flags:
                lines.append("**風險標記：**")
                lines.extend(f"- {flag}" for flag in dim.risk_flags)
                lines.append("")
            if dim and dim.verdict:
                lines.append(f"**維度結論：** {dim.verdict}")
                lines.append("")

        lines.extend(
            [
                "## 最後總結",
                "",
                f"**整體評級**：{report.overall_rating}  ",
                f"**建議倉位**：{report.suggested_position_size}  ",
                f"**入場價區間**：{report.entry_price_range}  ",
                f"**止蝕位**：{report.stop_loss}  ",
                "",
                "**主要買入理由：**",
            ]
        )
        lines.extend(f"- {reason}" for reason in report.main_buy_reasons)
        lines.extend(
            [
                "",
                f"**最大風險**：{report.max_risk}",
                "",
                f"**最終建議**：{report.final_recommendation}",
                "",
                "## 數據時效確認",
                "",
                report.realtime_data_note,
            ]
        )
        return "\n".join(lines)

    @classmethod
    def _find_missing_sections(cls, report: DeepCheckReport) -> list[str]:
        missing: list[str] = []
        field_map = {
            "management_quality": report.management_quality,
            "moat_and_ai_leadership": report.moat_and_ai_leadership,
            "macro_geopolitics": report.macro_geopolitics,
            "market_sentiment": report.market_sentiment,
            "technical_timing": report.technical_timing,
            "valuation_fairness": report.valuation_fairness,
            "catalysts_and_black_swans": report.catalysts_and_black_swans,
            "personal_fit": report.personal_fit,
        }
        for field_name, content in field_map.items():
            if len(content.strip()) < MIN_DIMENSION_CHARS:
                missing.append(field_name)

        found_ids = {dim.dimension_id for dim in report.dimensions}
        for dim_id in range(1, 9):
            if dim_id not in found_ids:
                missing.append(f"dimension_{dim_id}")

        return sorted(set(missing))

    def _parse_report(
        self,
        raw_response: str,
        ticker: str,
        company_name: str,
        user_profile: DeepCheckUserProfile,
    ) -> DeepCheckReport:
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
        data["user_profile"] = user_profile.model_dump()

        self._merge_dimensions_into_fields(data)

        if "main_buy_reasons" in data:
            data["main_buy_reasons"] = self._normalize_string_list(data["main_buy_reasons"])
        if "max_risk" in data:
            data["max_risk"] = self._normalize_text_field(data["max_risk"])
        if "final_recommendation" in data:
            data["final_recommendation"] = self._normalize_text_field(data["final_recommendation"])

        for _, field_name, _ in DIMENSION_SPECS:
            if field_name in data:
                data[field_name] = self._normalize_text_field(data[field_name])

        report = DeepCheckReport.model_validate(data)
        markdown = self._compose_report_markdown(report)
        return report.model_copy(update={"report_markdown": markdown})