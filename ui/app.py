"""Streamlit application entry."""

from __future__ import annotations

import sys
from pathlib import Path

# 把項目根目錄加入 Python 路徑（解決 ModuleNotFoundError）
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import streamlit.components.v1 as components

from agents import (
    DeepCheckAgent,
    FinalDecisionAgent,
    FundamentalReportAgent,
    TechnicalAnalysisAgent,
)
from agents.models import (
    DeepCheckReport,
    FinalDecisionReport,
    FundamentalReport,
    TechnicalAnalysisReport,
)
from utils.config import ConfigurationError

DARK_BG = "#0f172a"
CARD_BG = "#1e2937"
TEXT_MUTED = "#94a3b8"
MISSING_PREREQUISITE_MSG = (
    "請先執行「生成完整分析」或分別執行 Step 1、2、3 後，再按此按鈕。"
)

TAB_STEP1 = "Step 1: 基本面分析"
TAB_STEP2 = "Step 2: 深度買前檢查"
TAB_STEP3 = "Step 3: 技術面分析"
TAB_STEP4 = "Step 4: 最終投資決策"


def _inject_styles() -> None:
    st.markdown(
        f"""
        <style>
            .stApp {{
                background-color: {DARK_BG};
            }}
            [data-testid="stSidebar"] {{
                background-color: {CARD_BG};
            }}
            .main-header {{
                color: #f8fafc;
                font-size: 2rem;
                font-weight: 700;
                margin-bottom: 0.25rem;
            }}
            .sub-header {{
                color: {TEXT_MUTED};
                font-size: 1rem;
                margin-bottom: 1.5rem;
            }}
            .info-card {{
                background-color: {CARD_BG};
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 1.25rem 1.5rem;
                margin-bottom: 1rem;
            }}
            .info-card h3 {{
                color: #e2e8f0;
                font-size: 1rem;
                margin: 0 0 0.75rem 0;
            }}
            .info-card p {{
                color: {TEXT_MUTED};
                margin: 0;
                line-height: 1.6;
            }}
            div[data-testid="stButton"] > button {{
                background: linear-gradient(135deg, #0ea5e9, #2563eb);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0.75rem 1.5rem;
                font-weight: 600;
                width: 100%;
            }}
            div[data-testid="stButton"] > button:hover {{
                border: none;
                color: white;
                background: linear-gradient(135deg, #38bdf8, #3b82f6);
            }}
            .st-key-run_final_decision_btn button {{
                background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
                color: white !important;
                border: none !important;
            }}
            .st-key-run_final_decision_btn button:hover {{
                background: linear-gradient(135deg, #8b5cf6, #6d28d9) !important;
                color: white !important;
                border: none !important;
            }}
            .report-meta {{
                display: flex;
                gap: 1rem;
                flex-wrap: wrap;
                margin-bottom: 1rem;
            }}
            .report-badge {{
                background-color: #334155;
                color: #e2e8f0;
                padding: 0.35rem 0.75rem;
                border-radius: 999px;
                font-size: 0.85rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown('<p class="main-header">AI Stock Multi-Agent Analysis</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">輸入股票代碼，生成基本面、深度買前檢查、技術面或最終投資決策（Step 1 → 2 → 3 → 4）</p>',
        unsafe_allow_html=True,
    )


def _render_profile_sidebar() -> dict[str, str]:
    with st.sidebar:
        st.markdown("### 個人資料")
        st.caption("以下資料會用於深度買前檢查的個人匹配分析（Step 2）及最終投資決策（Step 4）。")

        available_capital = st.text_input(
            "可用資金",
            placeholder="例如：HK$300,000",
            key="available_capital",
        )
        risk_tolerance = st.selectbox(
            "風險承受力",
            options=["保守", "穩健", "平衡", "進取", "高風險"],
            index=2,
            key="risk_tolerance",
        )
        investment_horizon = st.selectbox(
            "投資期限",
            options=["短期（< 1 年）", "中期（1–3 年）", "長期（3–5 年）", "超長期（> 5 年）"],
            index=1,
            key="investment_horizon",
        )
        portfolio_concentration = st.text_input(
            "組合集中度（可選）",
            placeholder="例如：科技股佔組合約 40%",
            key="portfolio_concentration",
        )

    return {
        "available_capital": available_capital,
        "risk_tolerance": risk_tolerance,
        "investment_horizon": investment_horizon,
        "portfolio_concentration": portfolio_concentration,
    }


def _render_input_panel() -> str:
    with st.container():
        st.markdown(
            """
            <div class="info-card">
                <h3>分析設定</h3>
                <p>輸入美股代碼（如 AAPL、NVDA、GOOGL），可單獨生成各類報告，或一次執行 Step 1 → 2 → 3 → 4 完整分析。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ticker = st.text_input(
            "股票代碼",
            placeholder="NVDA",
            key="ticker_input",
        ).strip().upper()

    return ticker


def _render_fundamental_summary(report: FundamentalReport) -> None:
    st.markdown(
        f"""
        <div class="report-meta">
            <span class="report-badge">📌 {report.ticker} · {report.company_name}</span>
            <span class="report-badge">整體：{report.overall_view}</span>
            <span class="report-badge">建議：{report.recommendation}</span>
            <span class="report-badge">信心：{report.confidence}</span>
            <span class="report-badge">數據：{report.data_updated_at}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_deep_check_summary(report: DeepCheckReport) -> None:
    reasons = " · ".join(report.main_buy_reasons[:2]) if report.main_buy_reasons else "—"
    st.markdown(
        f"""
        <div class="report-meta">
            <span class="report-badge">🔍 {report.ticker} · {report.company_name}</span>
            <span class="report-badge">評級：{report.overall_rating}</span>
            <span class="report-badge">倉位：{report.suggested_position_size}</span>
            <span class="report-badge">入場：{report.entry_price_range}</span>
            <span class="report-badge">止蝕：{report.stop_loss}</span>
            <span class="report-badge">數據：{report.data_updated_at}</span>
        </div>
        <p style="color:{TEXT_MUTED};font-size:0.9rem;">主要理由：{reasons}</p>
        """,
        unsafe_allow_html=True,
    )


def _render_final_decision_summary(report: FinalDecisionReport) -> None:
    st.markdown(
        f"""
        <div class="report-meta">
            <span class="report-badge">🎯 {report.ticker} · {report.company_name}</span>
            <span class="report-badge">最終建議：{report.final_recommendation}</span>
            <span class="report-badge">信心：{report.conviction_level}</span>
            <span class="report-badge">倉位：{report.position_size}</span>
            <span class="report-badge">入場：{report.entry_price_range}</span>
            <span class="report-badge">止蝕：{report.stop_loss}</span>
            <span class="report-badge">數據：{report.data_updated_at}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_technical_summary(report: TechnicalAnalysisReport) -> None:
    st.markdown(
        f"""
        <div class="report-meta">
            <span class="report-badge">📉 {report.ticker} · {report.company_name}</span>
            <span class="report-badge">技術評級：{report.technical_rating}</span>
            <span class="report-badge">適合入場：{report.suitable_for_entry}</span>
            <span class="report-badge">入場：{report.entry_price_range}</span>
            <span class="report-badge">止蝕：{report.stop_loss}</span>
            <span class="report-badge">倉位：{report.position_size}</span>
            <span class="report-badge">數據：{report.data_updated_at}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_report_content(
    *,
    markdown: str,
    html: str,
    ticker: str,
    report_prefix: str,
    view_key: str,
    markdown_only: bool = False,
) -> None:
    has_html = bool(html and html.strip()) and not markdown_only

    if has_html:
        view_mode = st.radio(
            "報告格式",
            options=["Markdown 報告", "HTML 報告"],
            horizontal=True,
            key=view_key,
        )
    else:
        view_mode = "Markdown 報告"

    if view_mode == "Markdown 報告":
        st.markdown(markdown)
        st.download_button(
            label="下載報告（Markdown）",
            data=markdown,
            file_name=f"{ticker}_{report_prefix}.md",
            mime="text/markdown",
            use_container_width=True,
            key=f"download_md_{view_key}",
        )
    else:
        components.html(html, height=900, scrolling=True)
        st.download_button(
            label="下載報告（HTML）",
            data=html,
            file_name=f"{ticker}_{report_prefix}.html",
            mime="text/html",
            use_container_width=True,
            key=f"download_html_{view_key}",
        )


def _run_fundamental(ticker: str, *, show_spinner: bool = True) -> FundamentalReport | None:
    def _execute() -> FundamentalReport | None:
        try:
            return FundamentalReportAgent().run(ticker)
        except ConfigurationError as exc:
            st.error(f"API 設定錯誤：{exc}")
        except ValueError as exc:
            st.error(f"輸入錯誤：{exc}")
        except RuntimeError as exc:
            st.error(f"基本面分析失敗：{exc}")
        except Exception as exc:
            st.error(f"發生未預期錯誤：{exc}")
        return None

    if show_spinner:
        with st.spinner(f"Step 1：正在生成 {ticker} 基本面報告…（約 20–40 秒）"):
            return _execute()
    return _execute()


def _run_deep_check(
    ticker: str,
    profile: dict[str, str],
    *,
    show_spinner: bool = True,
) -> DeepCheckReport | None:
    def _execute() -> DeepCheckReport | None:
        try:
            return DeepCheckAgent().run(
                ticker,
                available_capital=profile.get("available_capital", ""),
                risk_tolerance=profile.get("risk_tolerance", ""),
                investment_horizon=profile.get("investment_horizon", ""),
                portfolio_concentration=profile.get("portfolio_concentration", ""),
            )
        except ConfigurationError as exc:
            st.error(f"API 設定錯誤：{exc}")
        except ValueError as exc:
            st.error(f"輸入錯誤：{exc}")
        except RuntimeError as exc:
            st.error(f"深度檢查失敗：{exc}")
        except Exception as exc:
            st.error(f"發生未預期錯誤：{exc}")
        return None

    if show_spinner:
        status = st.empty()
        status.info(f"Step 2：正在進行 {ticker} 深度買前檢查（交叉驗證 8 大維度）…")
        with st.spinner(f"深度檢查進行中…（約 25–45 秒，請勿關閉頁面）"):
            report = _execute()
        if report is not None:
            status.success(f"{ticker} 深度買前檢查完成。")
        return report
    return _execute()


def _run_technical(ticker: str, *, show_spinner: bool = True) -> TechnicalAnalysisReport | None:
    def _execute() -> TechnicalAnalysisReport | None:
        try:
            return TechnicalAnalysisAgent().run(ticker)
        except ConfigurationError as exc:
            st.error(f"API 設定錯誤：{exc}")
        except ValueError as exc:
            st.error(f"輸入錯誤：{exc}")
        except RuntimeError as exc:
            st.error(f"技術面分析失敗：{exc}")
        except Exception as exc:
            st.error(f"發生未預期錯誤：{exc}")
        return None

    if show_spinner:
        with st.spinner(f"Step 3：正在進行 {ticker} 技術面分析…（約 20–35 秒）"):
            return _execute()
    return _execute()


def _get_prerequisite_reports() -> tuple[FundamentalReport | None, DeepCheckReport | None, TechnicalAnalysisReport | None]:
    return (
        st.session_state.get("last_fundamental_report"),
        st.session_state.get("last_deep_check_report"),
        st.session_state.get("last_technical_report"),
    )


def _validate_prerequisite_reports(
    ticker: str,
    fundamental: FundamentalReport | None,
    deep_check: DeepCheckReport | None,
    technical: TechnicalAnalysisReport | None,
) -> bool:
    if fundamental is None or deep_check is None or technical is None:
        st.warning(MISSING_PREREQUISITE_MSG)
        return False

    report_tickers = {fundamental.ticker, deep_check.ticker, technical.ticker}
    if len(report_tickers) != 1 or ticker not in report_tickers:
        st.warning(
            f"現有報告股票代碼（{', '.join(sorted(report_tickers))}）"
            f"與目前輸入（{ticker}）不一致，請重新生成 Step 1–3 報告。"
        )
        return False

    return True


def _run_final_decision(
    fundamental: FundamentalReport,
    deep_check: DeepCheckReport,
    technical: TechnicalAnalysisReport,
    profile: dict[str, str],
    *,
    show_spinner: bool = True,
) -> FinalDecisionReport | None:
    def _execute() -> FinalDecisionReport | None:
        try:
            return FinalDecisionAgent().run(
                fundamental,
                deep_check,
                technical,
                user_profile=profile,
            )
        except ConfigurationError as exc:
            st.error(f"API 設定錯誤：{exc}")
        except ValueError as exc:
            st.error(f"輸入錯誤：{exc}")
        except RuntimeError as exc:
            st.error(f"最終決策分析失敗：{exc}")
        except Exception as exc:
            st.error(f"發生未預期錯誤：{exc}")
        return None

    if show_spinner:
        with st.spinner("Step 4: 正在進行最終投資決策..."):
            return _execute()
    return _execute()


def _run_full_analysis(ticker: str, profile: dict[str, str]) -> None:
    """Execute Step 1 → 2 → 3 → 4 with a four-stage progress bar."""
    st.session_state.pop("last_final_decision_report", None)

    progress = st.progress(0, text="Step 1: 正在進行基本面分析...")
    fundamental = _run_fundamental(ticker, show_spinner=False)
    if fundamental is None:
        st.error("Step 1 基本面分析失敗，完整分析已中止。")
        progress.empty()
        return
    st.session_state["last_fundamental_report"] = fundamental

    progress.progress(25, text="Step 2: 正在進行深度買前檢查...")
    deep_check = _run_deep_check(ticker, profile, show_spinner=False)
    if deep_check is None:
        st.error("Step 2 深度買前檢查失敗，完整分析已中止。")
        progress.empty()
        return
    st.session_state["last_deep_check_report"] = deep_check

    progress.progress(50, text="Step 3: 正在進行技術面分析...")
    technical = _run_technical(ticker, show_spinner=False)
    if technical is None:
        st.error("Step 3 技術面分析失敗，完整分析已中止。")
        progress.empty()
        return
    st.session_state["last_technical_report"] = technical

    progress.progress(75, text="Step 4: 正在進行最終投資決策...")
    final_report = _run_final_decision(
        fundamental,
        deep_check,
        technical,
        profile,
        show_spinner=False,
    )
    if final_report is None:
        st.error("Step 4 最終投資決策失敗，請稍後重試或使用「重新生成最終投資決策」。")
        progress.empty()
        return
    st.session_state["last_final_decision_report"] = final_report

    progress.progress(100, text="完整分析完成（Step 1 + 2 + 3 + 4）。")
    st.success(
        f"{ticker} 完整分析完成：最終建議 {final_report.final_recommendation}"
        f"（信心 {final_report.conviction_level}）。請查看「{TAB_STEP4}」tab。"
    )
    progress.empty()


def _validate_ticker(ticker: str) -> bool:
    if not ticker:
        st.warning("請輸入股票代碼。")
        return False
    return True


def run_app() -> None:
    st.set_page_config(
        page_title="AI Stock Multi-Agent Analysis",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _inject_styles()
    _render_header()
    profile = _render_profile_sidebar()
    ticker = _render_input_panel()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        run_fundamental_btn = st.button("生成基本面報告", use_container_width=True)
    with col2:
        run_deep_check_btn = st.button("生成深度買前檢查", use_container_width=True)
    with col3:
        run_technical_btn = st.button("生成技術面分析", use_container_width=True)
    with col4:
        run_full_btn = st.button("生成完整分析", type="primary", use_container_width=True)

    _, final_col, _ = st.columns([1, 2, 1])
    with final_col:
        run_final_btn = st.button(
            "重新生成最終投資決策",
            use_container_width=True,
            key="run_final_decision_btn",
        )
        st.caption("可在執行完整分析後，調整個人資料再重新生成 Step 4 的最終建議。")

    any_run = (
        run_fundamental_btn
        or run_deep_check_btn
        or run_technical_btn
        or run_final_btn
        or run_full_btn
    )
    if any_run:
        if not _validate_ticker(ticker):
            st.stop()
        st.session_state["last_profile"] = profile
        st.session_state["last_ticker"] = ticker

    if run_fundamental_btn:
        report = _run_fundamental(ticker)
        if report is not None:
            st.session_state["last_fundamental_report"] = report

    if run_deep_check_btn:
        report = _run_deep_check(ticker, profile)
        if report is not None:
            st.session_state["last_deep_check_report"] = report

    if run_technical_btn:
        report = _run_technical(ticker)
        if report is not None:
            st.session_state["last_technical_report"] = report

    if run_final_btn:
        fundamental_report, deep_check_report, technical_report = _get_prerequisite_reports()
        if _validate_prerequisite_reports(ticker, fundamental_report, deep_check_report, technical_report):
            final_report = _run_final_decision(
                fundamental_report,  # type: ignore[arg-type]
                deep_check_report,  # type: ignore[arg-type]
                technical_report,  # type: ignore[arg-type]
                profile,
            )
            if final_report is not None:
                st.session_state["last_final_decision_report"] = final_report

    if run_full_btn:
        _run_full_analysis(ticker, profile)

    fundamental_report = st.session_state.get("last_fundamental_report")
    deep_check_report = st.session_state.get("last_deep_check_report")
    technical_report = st.session_state.get("last_technical_report")
    final_decision_report = st.session_state.get("last_final_decision_report")

    if not fundamental_report and not deep_check_report and not technical_report and not final_decision_report:
        return

    st.markdown("---")
    tab_labels: list[str] = []
    if fundamental_report:
        tab_labels.append(TAB_STEP1)
    if deep_check_report:
        tab_labels.append(TAB_STEP2)
    if technical_report:
        tab_labels.append(TAB_STEP3)
    if final_decision_report:
        tab_labels.append(TAB_STEP4)

    tabs = st.tabs(tab_labels)
    tab_index = 0

    if fundamental_report:
        with tabs[tab_index]:
            _render_fundamental_summary(fundamental_report)
            _render_report_content(
                markdown=fundamental_report.report_markdown,
                html=fundamental_report.html_report,
                ticker=fundamental_report.ticker,
                report_prefix="fundamental_report",
                view_key="fundamental_view_mode",
            )
        tab_index += 1

    if deep_check_report:
        with tabs[tab_index]:
            _render_deep_check_summary(deep_check_report)
            deep_html = getattr(deep_check_report, "html_report", "") or ""
            _render_report_content(
                markdown=deep_check_report.report_markdown,
                html=deep_html,
                ticker=deep_check_report.ticker,
                report_prefix="deep_check_report",
                view_key="deep_check_view_mode",
            )
        tab_index += 1

    if technical_report:
        with tabs[tab_index]:
            _render_technical_summary(technical_report)
            _render_report_content(
                markdown=technical_report.report_markdown,
                html="",
                ticker=technical_report.ticker,
                report_prefix="technical_report",
                view_key="technical_view_mode",
                markdown_only=True,
            )
        tab_index += 1

    if final_decision_report:
        with tabs[tab_index]:
            _render_final_decision_summary(final_decision_report)
            _render_report_content(
                markdown=final_decision_report.report_markdown,
                html="",
                ticker=final_decision_report.ticker,
                report_prefix="final_decision_report",
                view_key="final_decision_view_mode",
                markdown_only=True,
            )


if __name__ == "__main__":
    run_app()