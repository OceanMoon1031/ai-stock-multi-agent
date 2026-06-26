# AI Stock Multi-Agent Analysis

**Live Demo:** [https://ai-stock-multi-agent-75d5nqefengwnuqvy94hpd.streamlit.app](https://ai-stock-multi-agent-75d5nqefengwnuqvy94hpd.streamlit.app)

A multi-agent stock analysis system that performs comprehensive fundamental, pre-purchase due diligence, technical, and final investment decision analysis using Grok (xAI) API.

---

## Project Overview

This project implements a **4-step multi-agent workflow** designed to simulate how a professional investment team would evaluate a stock.

Given a stock ticker and the user’s personal investment profile (capital, risk tolerance, investment horizon), the system generates structured, actionable investment recommendations.

### Key Highlights
- 4 specialized agents working in sequence (Fundamental → Deep Check → Technical → Final Decision)
- Structured outputs using Pydantic models for reliable, machine-readable reports
- Real-time market data integration via yfinance
- Personal risk profile matching in the final recommendation
- Fully deployed public demo on Streamlit Community Cloud

<image-card alt="Main UI" src="images/main-ui.png" ></image-card>

---

## Features

| Step | Agent | Description |
|------|-------|-------------|
| **Step 1** | Fundamental Analysis | Financial statements, KPIs, business segments, guidance vs expectations |
| **Step 2** | Pre-Purchase Deep Check | 8-dimension skeptical analysis (management, moat, macro, sentiment, valuation, black swans, personal fit, etc.) |
| **Step 3** | Technical Analysis | RSI, MACD, moving averages, support/resistance, chart patterns, entry strategy |
| **Step 4** | Final Investment Decision | Cross-report consistency check + personal profile matching → final rating + position sizing + entry/exit plan |

<image-card alt="Fundamental Analysis Example" src="images/step1_result1.png" ></image-card>

<image-card alt="Deep Check Analysis Example" src="images/step2_result1.png" ></image-card>

---

## Live Demo

Try it here: [https://ai-stock-multi-agent-75d5nqefengwnuqvy94hpd.streamlit.app](https://ai-stock-multi-agent-75d5nqefengwnuqvy94hpd.streamlit.app)

Recommended test tickers: `NVDA`, `AAPL`, `GOOGL`, `AMD`, `TSM`

<image-card alt="Final Investment Decision Example" src="images/final_result1.png" ></image-card>

---

## Tech Stack

- **LLM**: Grok-4 (xAI) via OpenAI-compatible API
- **Orchestration**: Custom multi-agent workflow (Streamlit)
- **Data**: yfinance + pandas + ta (technical indicators)
- **Structured Output**: Pydantic v2
- **Frontend**: Streamlit (dark theme)
- **Deployment**: Streamlit Community Cloud

---

## Project Structure

```text
ai-stock-multi-agent/
├── app.py                      # Entry point for Streamlit Cloud
├── ui/
│   └── app.py                  # Main UI + workflow controller
├── agents/
│   ├── fundamental_agent.py    # Step 1
│   ├── deep_check_agent.py     # Step 2
│   ├── technical_agent.py      # Step 3
│   ├── final_decision_agent.py # Step 4
│   └── models.py
├── tools/
│   ├── stock_data.py
│   └── technical_indicators.py
├── utils/
│   └── config.py
├── requirements.txt
└── Dockerfile
```
---

## Getting Started (Local)

git clone https://github.com/OceanMoon1031/ai-stock-multi-agent.git
cd ai-stock-multi-agent

pip install -r requirements.txt

# Create .env file with your Grok API key
echo "XAI_API_KEY=sk-your-key-here" > .env

streamlit run ui/app.py
---

## Author
Chan Hoi-Yuet (Moon)
BSc Computer Science, Hong Kong Metropolitan University

Interested in AI Engineering, LLM Applications, and Full-stack Development
Building practical AI agent systems and LLM-powered tools

---
## License
This project is for portfolio and educational demonstration purposes.
