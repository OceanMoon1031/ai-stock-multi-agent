"""Final integrated decision agent (Step 4) powered by xAI Grok."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from agents.models import (
    ConsistencyCheckItem,
    DeepCheckReport,
    DeepCheckUserProfile,
    FinalDecisionReport,
    FundamentalReport,
    RatingMapping,
    TechnicalAnalysisReport,
)
from utils.config import ConfigurationError, get_grok_client, get_settings

HKT = ZoneInfo("Asia/Hong_Kong")
MAX_ATTEMPTS = 2
MIN_CONSISTENCY_CHECKS = 4

SYSTEM_PROMPT = """你是一位擁有20年以上經驗的香港專業投資顧問，極度冷靜理性。
你的任務是整合三份已完成的股票分析報告（基本面、深度買前檢查、技術面），
給出最終、務實、保守的投資決策，重點回答「我而家應該點做」。

【評級統一映射 — 必須遵守】
三份報告使用不同評級體系，你必須先映射到統一尺度，再進行一致性檢查：

Step 1 recommendation 映射：
- Strong Buy → Strong Buy
- Buy → Buy
- Hold → Neutral
- Sell / Strong Sell → Avoid

Step 2 overall_rating 映射：
- Strong Buy → Strong Buy
- Buy → Buy
- Neutral → Neutral
- Avoid → Avoid

Step 3 technical_rating 映射：
- 強烈看多 → Strong Buy
- 看多 → Buy
- 中性 → Neutral
- 看空 / 強烈看空 → Avoid

【一致性檢查 — 必須嚴格執行】
你必須逐項檢查以下維度，並在 consistency_checks 中記錄：
1. 整體評級（映射後）
2. 入場價區間
3. 止蝕位
4. 倉位建議
5. 風險評估
每項必須說明三份報告的觀點、是否一致、分歧原因及你採納哪方邏輯。

【個人適合度 — 必須重新評估】
必須結合用戶個人資料（可用資金、風險承受力、投資期限、組合集中度）
在 personal_fit_reassessment 中重新評估，唔可以只重複 Step 2 結論。

【最終建議原則】
- 保守務實：有明顯分歧時，降低 conviction_level 同倉位。
- 技術面「觀望/否」但基本面強勁 → 可 Buy 但縮細倉位、等更好入場。
- 基本面 Avoid 但技術面看多 → 通常 Neutral 或 Avoid，並解釋。
- entry_plan 必須具體（分批比例、觸發條件、時間框架）。
- deal_breakers 必須是可監察的具體條件。

【數據誠信】
只能使用用戶提供的三份報告內容；禁止虛構新數據或股價。
缺失資料必須標註。

【輸出格式】只返回有效 JSON，無 markdown fence，無額外文字。"""

JSON_SCHEMA_HINT = """
{
  "ticker": "string",
  "company_name": "string",
  "analysis_date": "string",
  "data_updated_at": "string",
  "rating_mapping": {
    "step1_raw": "string",
    "step2_raw": "string",
    "step3_raw": "string",
    "step1_mapped": "Strong Buy|Buy|Neutral|Avoid",
    "step2_mapped": "Strong Buy|Buy|Neutral|Avoid",
    "step3_mapped": "Strong Buy|Buy|Neutral|Avoid",
    "mapping_notes": "string"
  },
  "consistency_checks": [
    {
      "aspect": "整體評級|入場價|止蝕|倉位建議|風險",
      "step1_view": "string",
      "step2_view": "string",
      "step3_view": "string",
      "is_consistent": true,
      "explanation": "string"
    }
  ],
  "personal_fit_reassessment": "string (詳細，至少 6 句)",
  "final_recommendation": "Strong Buy|Buy|Neutral|Avoid",
  "conviction_level": "High|Medium|Low",
  "conviction_rationale": "string",
  "position_size": "string (具體百分比)",
  "entry_price_range": "string",
  "stop_loss": "string",
  "take_profit_1": "string",
  "take_profit_2": "string",
  "entry_plan": "string (分批計劃，具體)",
  "key_risks": ["string"],
  "deal_breakers": ["string"],
  "report_markdown": "string (可簡短，系統會重組)"
}"""


class FinalDecisionAgent:
    """Agent that synthesizes Step 1–3 reports into a final investment decision."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or get_settings().xai_model

    def run(
        self,
        fundamental: FundamentalReport,
        deep_check: DeepCheckReport,
        technical: TechnicalAnalysisReport,
        *,
        user_profile: dict[str, str] | None = None,
    ) -> FinalDecisionReport:
        """Integrate three reports and produce a final decision."""
        self._validate_inputs(fundamental, deep_check, technical)

        profile = self._resolve_user_profile(user_profile, deep_check)
        prompt = self._build_prompt(fundamental, deep_check, technical, profile)

        last_error: str | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                raw_response = self._call_grok(
                    prompt if attempt == 1 else self._build_retry_prompt(prompt, attempt)
                )
                report = self._parse_report(
                    raw_response,
                    fundamental,
                    deep_check,
                    technical,
                    profile,
                )
                issues = self._find_issues(report)
                if not issues:
                    return report
                last_error = f"Incomplete output (attempt {attempt}): {issues}"
            except (RuntimeError, ValueError) as exc:
                last_error = str(exc)

        raise RuntimeError(
            f"Final decision failed after {MAX_ATTEMPTS} attempts. Last issue: {last_error}"
        )

    @staticmethod
    def _validate_inputs(
        fundamental: FundamentalReport,
        deep_check: DeepCheckReport,
        technical: TechnicalAnalysisReport,
    ) -> None:
        tickers = {fundamental.ticker, deep_check.ticker, technical.ticker}
        if len(tickers) != 1:
            raise ValueError(
                f"Ticker mismatch across reports: {sorted(tickers)}. "
                "All three reports must be for the same symbol."
            )

    @staticmethod
    def _resolve_user_profile(
        user_profile: dict[str, str] | None,
        deep_check: DeepCheckReport,
    ) -> DeepCheckUserProfile:
        if user_profile:
            return DeepCheckUserProfile(
                available_capital=user_profile.get("available_capital", ""),
                risk_tolerance=user_profile.get("risk_tolerance", ""),
                investment_horizon=user_profile.get("investment_horizon", ""),
                portfolio_concentration=user_profile.get("portfolio_concentration", ""),
            )
        return deep_check.user_profile

    @staticmethod
    def _now_hkt() -> datetime:
        return datetime.now(HKT)

    def _build_prompt(
        self,
        fundamental: FundamentalReport,
        deep_check: DeepCheckReport,
        technical: TechnicalAnalysisReport,
        user_profile: DeepCheckUserProfile,
    ) -> str:
        now = self._now_hkt()
        analysis_date = now.strftime("%Y年%m月%d日")
        data_updated_at = now.strftime("截至%Y年%m月%d日 %H:%M HKT")

        step1_summary = {
            "recommendation": fundamental.recommendation,
            "overall_view": fundamental.overall_view,
            "confidence": fundamental.confidence,
            "suggested_buy_price": fundamental.suggested_buy_price,
            "take_profit_price": fundamental.take_profit_price,
            "stop_loss_price": fundamental.stop_loss_price,
            "investment_strategy": fundamental.investment_strategy,
            "executive_summary": fundamental.executive_summary[:800],
            "valuation_assessment": fundamental.valuation_assessment[:600],
            "risk_factors": fundamental.risk_factors[:5],
            "top_risks": [
                {"title": r.title, "impact_level": r.impact_level}
                for r in fundamental.risk_factors_detail[:4]
            ],
        }
        step2_summary = {
            "overall_rating": deep_check.overall_rating,
            "suggested_position_size": deep_check.suggested_position_size,
            "entry_price_range": deep_check.entry_price_range,
            "stop_loss": deep_check.stop_loss,
            "main_buy_reasons": deep_check.main_buy_reasons,
            "max_risk": deep_check.max_risk,
            "final_recommendation": deep_check.final_recommendation[:600],
            "personal_fit": deep_check.personal_fit[:600],
            "valuation_fairness": deep_check.valuation_fairness[:400],
            "technical_timing": deep_check.technical_timing[:400],
        }
        step3_summary = {
            "technical_rating": technical.technical_rating,
            "suitable_for_entry": technical.suitable_for_entry,
            "entry_price_range": technical.entry_price_range,
            "stop_loss": technical.stop_loss,
            "take_profit_1": technical.take_profit_1,
            "take_profit_2": technical.take_profit_2,
            "position_size": technical.position_size,
            "technical_conclusion": technical.technical_conclusion[:600],
            "entry_strategy": technical.entry_strategy[:600],
            "risk_warnings": technical.risk_warnings[:500],
        }

        payload = {
            "step1_fundamental": step1_summary,
            "step2_deep_check": step2_summary,
            "step3_technical": step3_summary,
            "user_profile": user_profile.model_dump(),
        }
        data_json = json.dumps(payload, indent=2, ensure_ascii=False)

        return f"""請整合以下三份已完成報告，生成 Step 4 最終投資決策。

股票代碼：{fundamental.ticker}
公司名稱：{fundamental.company_name}
整合分析日期：{analysis_date}
數據更新時間：{data_updated_at}

【用戶個人資料 — 必須用於 personal_fit_reassessment】
- 可用資金：{user_profile.available_capital or "未提供"}
- 風險承受力：{user_profile.risk_tolerance or "未提供"}
- 投資期限：{user_profile.investment_horizon or "未提供"}
- 組合集中度：{user_profile.portfolio_concentration or "未提供"}

【三份報告來源時間】
- Step 1：{fundamental.data_updated_at}
- Step 2：{deep_check.data_updated_at}
- Step 3：{technical.data_updated_at}

=== 三份報告結構化摘要 (JSON) ===
{data_json}

=== 輸出檢查清單 ===
□ rating_mapping 完整（含 mapping_notes）
□ consistency_checks 至少 5 項（整體評級、入場價、止蝕、倉位、風險）
□ personal_fit_reassessment 詳細且結合用戶資料
□ final_recommendation + conviction_level + conviction_rationale
□ 具體 position_size、entry_price_range、stop_loss、take_profit、entry_plan
□ key_risks 至少 3 項、deal_breakers 至少 2 項

JSON schema:
{JSON_SCHEMA_HINT}

只返回 JSON。"""

    @staticmethod
    def _build_retry_prompt(base_prompt: str, attempt: int) -> str:
        return f"""{base_prompt}

【⚠️ 重試第 {attempt} 次 — 上次輸出不完整】
你必須補齊：
1. consistency_checks 至少 5 項
2. personal_fit_reassessment 至少 6 句
3. entry_plan 具體分批計劃
4. key_risks 至少 3 項、deal_breakers 至少 2 項

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
                temperature=0.22,
                max_tokens=12000,
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
    def _compose_report_markdown(cls, report: FinalDecisionReport) -> str:
        lines = [
            f"# {report.company_name} ({report.ticker}) 最終投資決策報告",
            "",
            f"**整合分析日期**：{report.analysis_date}  ",
            f"**數據更新時間**：{report.data_updated_at}  ",
            f"**最終建議**：{report.final_recommendation}  ",
            f"**信心水平**：{report.conviction_level}  ",
            "",
            "## 執行摘要",
            "",
            report.conviction_rationale,
            "",
            "## 評級映射",
            "",
            f"- **Step 1（基本面）**：{report.rating_mapping.step1_raw} → {report.rating_mapping.step1_mapped}",
            f"- **Step 2（深度檢查）**：{report.rating_mapping.step2_raw} → {report.rating_mapping.step2_mapped}",
            f"- **Step 3（技術面）**：{report.rating_mapping.step3_raw} → {report.rating_mapping.step3_mapped}",
            "",
            report.rating_mapping.mapping_notes,
            "",
            "## 一致性檢查",
            "",
        ]

        for item in report.consistency_checks:
            status = "✅ 一致" if item.is_consistent else "⚠️ 分歧"
            lines.extend(
                [
                    f"### {item.aspect} — {status}",
                    "",
                    f"- **Step 1**：{item.step1_view}",
                    f"- **Step 2**：{item.step2_view}",
                    f"- **Step 3**：{item.step3_view}",
                    "",
                    item.explanation,
                    "",
                ]
            )

        lines.extend(
            [
                "## 個人適合度重新評估",
                "",
                report.personal_fit_reassessment,
                "",
                "## 具體行動建議",
                "",
                f"- **建議倉位**：{report.position_size}",
                f"- **入場價區間**：{report.entry_price_range}",
                f"- **止蝕位**：{report.stop_loss}",
                f"- **止盈目標 1**：{report.take_profit_1}",
                f"- **止盈目標 2**：{report.take_profit_2}",
                "",
                "### 分批入場計劃",
                "",
                report.entry_plan,
                "",
                "## 主要風險",
                "",
            ]
        )
        lines.extend(f"- {risk}" for risk in report.key_risks)
        lines.extend(["", "## 失效條件（Deal Breakers）", ""])
        lines.extend(f"- {breaker}" for breaker in report.deal_breakers)

        profile = report.user_profile
        lines.extend(
            [
                "",
                "## 用戶資料參考",
                "",
                f"- 可用資金：{profile.available_capital or '未提供'}",
                f"- 風險承受力：{profile.risk_tolerance or '未提供'}",
                f"- 投資期限：{profile.investment_horizon or '未提供'}",
                f"- 組合集中度：{profile.portfolio_concentration or '未提供'}",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def _find_issues(cls, report: FinalDecisionReport) -> list[str]:
        issues: list[str] = []
        if len(report.consistency_checks) < MIN_CONSISTENCY_CHECKS:
            issues.append(f"consistency_checks < {MIN_CONSISTENCY_CHECKS}")
        if len(report.personal_fit_reassessment.strip()) < 80:
            issues.append("personal_fit_reassessment too short")
        if len(report.entry_plan.strip()) < 40:
            issues.append("entry_plan too short")
        if len(report.key_risks) < 3:
            issues.append("key_risks < 3")
        if len(report.deal_breakers) < 2:
            issues.append("deal_breakers < 2")
        if not report.conviction_rationale.strip():
            issues.append("missing conviction_rationale")
        return issues

    def _parse_report(
        self,
        raw_response: str,
        fundamental: FundamentalReport,
        deep_check: DeepCheckReport,
        technical: TechnicalAnalysisReport,
        user_profile: DeepCheckUserProfile,
    ) -> FinalDecisionReport:
        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse Grok response as JSON: {exc}") from exc

        now = self._now_hkt()
        data.setdefault("ticker", fundamental.ticker)
        data.setdefault("company_name", fundamental.company_name)
        data.setdefault("analysis_date", now.strftime("%Y年%m月%d日"))
        data.setdefault("data_updated_at", now.strftime("截至%Y年%m月%d日 %H:%M HKT"))
        data["user_profile"] = user_profile.model_dump()

        if "key_risks" in data:
            data["key_risks"] = self._normalize_string_list(data["key_risks"])
        if "deal_breakers" in data:
            data["deal_breakers"] = self._normalize_string_list(data["deal_breakers"])
        for key in (
            "personal_fit_reassessment",
            "conviction_rationale",
            "entry_plan",
            "position_size",
            "entry_price_range",
            "stop_loss",
            "take_profit_1",
            "take_profit_2",
        ):
            if key in data:
                data[key] = self._normalize_text_field(data[key])

        if isinstance(data.get("rating_mapping"), dict):
            mapping = data["rating_mapping"]
            if "mapping_notes" in mapping:
                mapping["mapping_notes"] = self._normalize_text_field(mapping["mapping_notes"])

        if isinstance(data.get("consistency_checks"), list):
            normalized_checks: list[dict[str, Any]] = []
            for item in data["consistency_checks"]:
                if not isinstance(item, dict):
                    continue
                row = dict(item)
                for key in ("aspect", "step1_view", "step2_view", "step3_view", "explanation"):
                    if key in row:
                        row[key] = self._normalize_text_field(row[key])
                normalized_checks.append(row)
            data["consistency_checks"] = normalized_checks

        report = FinalDecisionReport.model_validate(data)
        markdown = self._compose_report_markdown(report)
        return report.model_copy(update={"report_markdown": markdown})