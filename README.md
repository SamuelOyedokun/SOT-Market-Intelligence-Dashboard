# 📈 SOT Market Intelligence Dashboard

> **Real-time market intelligence for US Stocks, Crypto, NGX, and Commodities**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://sot-market-intelligence-dashboard.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🌍 Live Demo

**[→ Launch Dashboard](https://sot-market-intelligence-dashboard.streamlit.app)**

---

## Overview

SOT Market Intelligence is a production-grade financial analytics platform that aggregates live market data across four asset classes, applies AI-powered analysis, and delivers professional-grade insights in a single unified interface. Built as a full-stack Python application deployed on Streamlit Cloud with real-time data from multiple API sources.

---

## Features

### 📊 Chart & Technical Analysis
- Live candlestick charts with configurable time periods (1M to 5Y)
- Technical indicators: MA20/MA50 moving averages, Bollinger Bands, RSI (14), Volume
- Key statistics panel — period return, annual volatility, RSI signal, volume vs average
- Supports all four markets from a single interface

### 💼 Portfolio Simulator
- Virtual $10,000 starting capital with full buy/sell order execution
- Real-time P&L tracking against live market prices
- Portfolio allocation pie chart and P&L bar chart per holding
- Trade history log with timestamps
- Average cost basis calculation for multi-leg positions

### 📰 News & Sentiment Analysis
- Real-time RSS aggregation from 10+ curated financial sources
- Asset-aware filtering with 50+ alias mappings (e.g. Apple → AAPL, iPhone, MacBook, iOS)
- Dedicated Nigerian sources for NGX stocks: Nairametrics, BusinessDay NG, Punch Business, Vanguard
- AI sentiment scoring (Positive / Neutral / Negative) via Groq LLaMA 3.3 70B
- Batch scoring with graceful fallback to keyword analysis
- Sentiment distribution charts and source breakdown

### 🏆 Market Overview
- Real-time heatmap across 9 key global assets
- Normalised 3-month performance comparison chart (Apple, Microsoft, NVIDIA, Bitcoin)
- Colour-coded positive/negative performance indicators

### 🤖 AI Market Insights
- 6 analysis types: Stock Summary, Technical Analysis, Sentiment Report, Risk Assessment, Macro Commentary, Investment Thesis
- Powered by Groq AI (LLaMA 3.3 70B) with OpenRouter as automatic fallback
- Live market data injected into every prompt for contextual accuracy
- Downloadable analysis reports as `.txt` files

### 🔔 Price Alert System
- Set above/below price alerts for any asset across all four markets
- Auto-checks on every page load with manual check button
- Email notifications via Gmail SMTP with branded HTML templates
- Alert history tracking with distance-to-trigger display

### 🔮 Market Forecast
- Machine Learning forecast using Linear Regression with lag features (lag1, lag2, lag5, rolling mean)
- Moving Average Projection with mean-reversion momentum model
- Configurable forecast horizon: 7, 14, 30, 60, 90 days
- Confidence bands with volatility-scaled uncertainty ranges
- Forecast summary table with consensus signal (Bullish / Neutral / Bearish)
- Support & Resistance levels from 90-day percentile analysis

---

## Markets Covered

| Market | Assets | Data Source |
|---|---|---|
| 🇺🇸 US Stocks | Apple, Microsoft, Google, Amazon, Tesla, NVIDIA, Meta, Netflix, JPMorgan, Coca-Cola | Yahoo Finance |
| ₿ Crypto | Bitcoin, Ethereum, BNB, Solana, XRP, Cardano, Dogecoin, Polkadot | Yahoo Finance |
| 🇳🇬 NGX Stocks | GTBank, Zenith Bank, MTN Nigeria, Dangote Cement, Access Bank, UBA, FBN Holdings, Stanbic IBTC, and more | iTick API |
| 🛢 Commodities | Gold, Silver, Crude Oil (WTI), Brent Crude, Natural Gas, Copper, Platinum, Corn, Wheat, Coffee | Yahoo Finance |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit, Plotly, HTML/CSS |
| Data | Yahoo Finance (yfinance), iTick API, RSS Feeds |
| AI | Groq API (LLaMA 3.3 70B), OpenRouter (fallback) |
| ML | scikit-learn (LinearRegression, MinMaxScaler) |
| Alerts | Gmail SMTP |
| Language | Python 3.11 |
| Deployment | Streamlit Cloud |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SOT Market Intelligence               │
├──────────────┬──────────────┬───────────────────────────┤
│  Data Layer  │  AI Layer    │  Presentation Layer        │
│              │              │                            │
│  yFinance    │  Groq AI     │  Streamlit UI              │
│  iTick API   │  OpenRouter  │  Plotly Charts             │
│  RSS Feeds   │  (fallback)  │  7-Tab Dashboard           │
│  Gmail SMTP  │  LLaMA 3.3   │  Live Price Metrics        │
└──────────────┴──────────────┴───────────────────────────┘
```

---

## Setup & Deployment

### Prerequisites
- Python 3.11+
- Streamlit Cloud account (for deployment)
- API keys (see below)

### Local Development

```bash
# Clone the repository
git clone https://github.com/SamuelOyedokun/sot-market-intelligence-dashboard
cd sot-market-intelligence-dashboard

# Install dependencies
pip install -r requirements.txt

# Create secrets file
mkdir .streamlit
touch .streamlit/secrets.toml
```

Add your API keys to `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY          = "your_groq_key"
OPENROUTER_API_KEY    = "your_openrouter_key"
ITICK_API_TOKEN       = "your_itick_token"
ALERT_SENDER_EMAIL    = "yourgmail@gmail.com"
ALERT_SENDER_PASSWORD = "your_gmail_app_password"
NEWS_API_KEY          = "your_newsapi_key"
```

```bash
# Run the app
streamlit run app.py
```

### Streamlit Cloud Deployment

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo, branch `main`, main file `app.py`
4. Add all secrets under **Settings → Secrets**
5. Click **Deploy**

---

## API Keys Required

| Key | Source | Free Tier |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | ✅ Free |
| `OPENROUTER_API_KEY` | [openrouter.ai](https://openrouter.ai) | ✅ Free |
| `ITICK_API_TOKEN` | [itick.io](https://itick.io) | ✅ Free (5 calls/min) |
| `ALERT_SENDER_EMAIL` | Gmail | ✅ Free |
| `ALERT_SENDER_PASSWORD` | Gmail App Password | ✅ Free |
| `NEWS_API_KEY` | [newsapi.org](https://newsapi.org) | ✅ Free tier |

> **Note:** Gmail requires a 16-character App Password, not your regular password. Generate one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

---

## NGX Data Strategy

Nigerian Stock Exchange (NGX) data is not available on Yahoo Finance. The app uses a three-tier fallback:

1. **iTick API** — Primary source. Real-time NGX prices via REST API. Requires valid token.
2. **Web Scraping** — Fallback when iTick is unavailable. Scrapes NGX-listed financial sites.
3. **Last Known Prices** — Hardcoded March 2026 prices used as final fallback to prevent app crashes.

> iTick free plan allows 5 API calls per minute. The app respects this limit with caching.

---

## Project Structure

```
sot-market-intelligence-dashboard/
├── app.py              # Main application (all tabs, logic, UI)
├── ngx_data.py         # NGX data module (iTick API, scraping, fallback)
├── requirements.txt    # Python dependencies
├── .python-version     # Python version lock (3.11)
├── packages.txt        # System packages for Streamlit Cloud
└── README.md           # This file
```

---

## Screenshots

| Tab | Description |
|---|---|
| 📊 Chart & Analysis | Candlestick chart with MA, Bollinger Bands, RSI |
| 💼 Portfolio Tracker | Virtual portfolio with real-time P&L |
| 📰 News & Sentiment | AI-scored articles from 10+ sources |
| 🏆 Market Overview | Cross-asset heatmap and performance chart |
| 🤖 AI Insights | 6 AI analysis types with downloadable reports |
| 🔔 Price Alerts | Email alert system with live price distance |
| 🔮 Market Forecast | ML + MA forecasting with confidence bands |

---

## Roadmap

- [ ] WhatsApp alert integration (Meta Cloud API)
- [ ] Additional NGX stocks (currently 15 covered)
- [ ] Mobile-optimised responsive layout
- [ ] Options chain data for US stocks
- [ ] Multi-asset correlation matrix
- [ ] Scheduled daily email digest

---

## Author

**Samuel Oyedokun**
- GitHub: [@SamuelOyedokun](https://github.com/SamuelOyedokun)
- LinkedIn: [samuel-oyedokun](https://www.linkedin.com/in/samuel-oyedokun-b41895142)
- Live Dashboard: [SOT Market Intelligence](https://sot-market-intelligence-dashboard.streamlit.app)

---

## Disclaimer

This dashboard is built for educational and informational purposes only. The AI-generated analysis, price forecasts, and market insights do not constitute financial advice. Always conduct your own research and consult a qualified financial advisor before making investment decisions. Past performance and model predictions do not guarantee future results.

---

## License

MIT License — free to use, modify, and distribute with attribution.
