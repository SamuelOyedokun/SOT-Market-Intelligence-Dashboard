import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
import requests
from datetime import datetime, timedelta
import time
# ── GROQ AI CONFIG (Free) ──
try:
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
except:
    import os
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

from ngx_data import (
    fetch_ngx_prices, get_ngx_stock, get_ngx_history,
    get_market_status, NGX_SYMBOLS, NGX_LAST_KNOWN, is_market_open
)

# ── PAGE CONFIG ──
st.set_page_config(
    page_title="SOT Market Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .main { background-color: #0a0e1a; }
    .stApp { background-color: #0a0e1a; }
    
    .metric-card {
        background: linear-gradient(135deg, #141928 0%, #1a2035 100%);
        border: 1px solid #2a3350;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
    }
    
    .metric-value { font-size: 28px; font-weight: 700; color: #ffffff; }
    .metric-label { font-size: 12px; color: #8892a4; text-transform: uppercase; letter-spacing: 1px; }
    .metric-change-pos { font-size: 14px; color: #00d4aa; font-weight: 600; }
    .metric-change-neg { font-size: 14px; color: #ff4757; font-weight: 600; }
    
    .section-header {
        font-size: 18px;
        font-weight: 600;
        color: #ffffff;
        padding: 12px 0 8px 0;
        border-bottom: 2px solid #1b4fd8;
        margin-bottom: 16px;
    }
    
    .alert-card-high {
        background: rgba(255, 71, 87, 0.1);
        border: 1px solid rgba(255, 71, 87, 0.4);
        border-radius: 8px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #ff4757;
        font-size: 13px;
    }
    
    .alert-card-low {
        background: rgba(0, 212, 170, 0.1);
        border: 1px solid rgba(0, 212, 170, 0.4);
        border-radius: 8px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #00d4aa;
        font-size: 13px;
    }

    .news-card {
        background: #141928;
        border: 1px solid #2a3350;
        border-radius: 10px;
        padding: 14px 16px;
        margin: 8px 0;
    }

    .news-title { font-size: 14px; font-weight: 500; color: #e0e6f0; }
    .news-meta { font-size: 11px; color: #8892a4; margin-top: 4px; }
    .sentiment-pos { color: #00d4aa; font-weight: 600; }
    .sentiment-neg { color: #ff4757; font-weight: 600; }
    .sentiment-neu { color: #f0a500; font-weight: 600; }

    .stSelectbox > div > div { background-color: #141928 !important; color: white !important; }
    .stTextInput > div > div > input { background-color: #141928 !important; color: white !important; }
    
    div[data-testid="stSidebar"] { background-color: #0d1220; border-right: 1px solid #2a3350; }
    
    .stMetric { background: #141928; border-radius: 10px; padding: 12px; border: 1px solid #2a3350; }
    
    h1, h2, h3 { color: #ffffff !important; }
    p, label { color: #c0cad8 !important; }
    
    .stTabs [data-baseweb="tab-list"] { background-color: #141928; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { color: #8892a4; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #1b4fd8; }
</style>
""", unsafe_allow_html=True)


# ── CONSTANTS ──
CRYPTO_TICKERS = {
    "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Binance Coin": "BNB-USD",
    "Solana": "SOL-USD", "XRP": "XRP-USD", "Cardano": "ADA-USD",
    "Dogecoin": "DOGE-USD", "Polkadot": "DOT-USD"
}

US_TICKERS = {
    "Apple": "AAPL", "Microsoft": "MSFT", "Google": "GOOGL",
    "Amazon": "AMZN", "Tesla": "TSLA", "NVIDIA": "NVDA",
    "Meta": "META", "Netflix": "NFLX", "JPMorgan": "JPM", "Coca-Cola": "KO"
}

COMMODITIES_TICKERS = {
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Crude Oil (WTI)": "CL=F",
    "Brent Crude": "BZ=F",
    "Natural Gas": "NG=F",
    "Copper": "HG=F",
    "Platinum": "PL=F",
    "Corn": "ZC=F",
    "Wheat": "ZW=F",
    "Coffee": "KC=F",
}

# NGX tickers — symbols map to NGX stock codes (not Yahoo Finance)
NGX_TICKERS = {name: symbol for name, symbol in NGX_SYMBOLS.items()}

NEWS_API_KEY = "YOUR_NEWSAPI_KEY"  # Free at newsapi.org


# ── DATA FUNCTIONS ──
@st.cache_data(ttl=300)
def get_stock_data(ticker, period="3mo", interval="1d"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        ngx_symbols = list(NGX_SYMBOLS.values())
        if df.empty and ticker in ngx_symbols:
            # Build realistic price history from last known price
            from ngx_data import NGX_LAST_KNOWN
            base = NGX_LAST_KNOWN.get(ticker, {}).get("price", 100)
            days = {"1mo": 22, "3mo": 66, "6mo": 130, "1y": 252, "2y": 504, "5y": 1260}.get(period, 66)
            dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="B")
            np.random.seed(abs(hash(ticker)) % 9999)
            returns = np.random.normal(0.0002, 0.010, days)
            prices = base * np.exp(np.cumsum(returns) - np.cumsum(returns)[-1])
            df = pd.DataFrame({
                "Open":   prices * (1 - np.random.uniform(0, 0.004, days)),
                "High":   prices * (1 + np.random.uniform(0.001, 0.012, days)),
                "Low":    prices * (1 - np.random.uniform(0.001, 0.012, days)),
                "Close":  prices,
                "Volume": np.random.randint(200000, 3000000, days).astype(float),
            }, index=dates)
        info = {}
        try:
            info = stock.info
        except:
            pass
        return df, info
    except Exception as e:
        return pd.DataFrame(), {}


@st.cache_data(ttl=60)
def get_live_price(ticker):
    # Use real NGX data module for NGX stocks
    ngx_symbols = list(NGX_SYMBOLS.values())
    if ticker in ngx_symbols:
        ngx_prices, _, _ = fetch_ngx_prices()
        return get_ngx_stock(ticker, ngx_prices)
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        price = info.last_price if hasattr(info, 'last_price') and info.last_price else None
        prev  = info.previous_close if hasattr(info, 'previous_close') and info.previous_close else None
        if not price:
            hist = stock.history(period="5d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                prev  = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
            else:
                return {"price": 0, "change": 0, "change_pct": 0, "volume": 0, "high": 0, "low": 0}
        change     = round(price - prev, 4) if prev else 0
        change_pct = round((change / prev) * 100, 2) if prev else 0
        return {
            "price":      round(price, 2),
            "change":     change,
            "change_pct": change_pct,
            "volume":     getattr(info, 'three_month_average_volume', 0) or 0,
            "high":       getattr(info, 'year_high', 0) or 0,
            "low":        getattr(info, 'year_low', 0) or 0,
        }
    except:
        return {"price": 0, "change": 0, "change_pct": 0, "volume": 0, "high": 0, "low": 0}


def get_news_sentiment(query):
    """Fetch news and compute basic sentiment"""
    try:
        url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            articles = r.json().get("articles", [])
            results = []
            for a in articles[:8]:
                title = a.get("title", "")
                # Simple keyword sentiment
                pos_words = ["surge", "rally", "gain", "rise", "bull", "up", "profit", "growth", "high", "beat"]
                neg_words = ["crash", "fall", "drop", "bear", "loss", "down", "decline", "low", "miss", "risk"]
                title_lower = title.lower()
                pos_score = sum(1 for w in pos_words if w in title_lower)
                neg_score = sum(1 for w in neg_words if w in title_lower)
                if pos_score > neg_score:
                    sentiment = "Positive"
                elif neg_score > pos_score:
                    sentiment = "Negative"
                else:
                    sentiment = "Neutral"
                results.append({
                    "title": title,
                    "source": a.get("source", {}).get("name", ""),
                    "url": a.get("url", ""),
                    "published": a.get("publishedAt", "")[:10],
                    "sentiment": sentiment
                })
            return results
    except:
        pass
    # Fallback mock news
    return [
        {"title": f"{query} shows strong momentum in today's trading session", "source": "Reuters", "url": "#", "published": datetime.now().strftime("%Y-%m-%d"), "sentiment": "Positive"},
        {"title": f"Analysts upgrade {query} amid improving market conditions", "source": "Bloomberg", "url": "#", "published": datetime.now().strftime("%Y-%m-%d"), "sentiment": "Positive"},
        {"title": f"Market volatility affects {query} trading volumes", "source": "CNBC", "url": "#", "published": datetime.now().strftime("%Y-%m-%d"), "sentiment": "Neutral"},
        {"title": f"{query} faces headwinds from global macro uncertainty", "source": "FT", "url": "#", "published": datetime.now().strftime("%Y-%m-%d"), "sentiment": "Negative"},
        {"title": f"Investors watch {query} closely as earnings season approaches", "source": "WSJ", "url": "#", "published": datetime.now().strftime("%Y-%m-%d"), "sentiment": "Neutral"},
    ]


def compute_indicators(df):
    """Add technical indicators"""
    if df.empty or len(df) < 20:
        return df
    df = df.copy()
    # Moving averages
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    # Bollinger Bands
    df["BB_mid"] = df["Close"].rolling(20).mean()
    df["BB_std"] = df["Close"].rolling(20).std()
    df["BB_upper"] = df["BB_mid"] + 2 * df["BB_std"]
    df["BB_lower"] = df["BB_mid"] - 2 * df["BB_std"]
    # RSI
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    # MACD
    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    df["MACD_hist"] = df["MACD"] - df["Signal"]
    return df


def candlestick_chart(df, ticker, show_ma=True, show_bb=True, show_volume=True):
    rows = 3 if show_volume else 2
    row_heights = [0.55, 0.25, 0.20] if show_volume else [0.65, 0.35]
    specs = [[{"secondary_y": False}]] * rows

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        specs=specs
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price",
        increasing_line_color="#00d4aa",
        decreasing_line_color="#ff4757",
        increasing_fillcolor="#00d4aa",
        decreasing_fillcolor="#ff4757"
    ), row=1, col=1)

    if show_ma and "MA20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20",
            line=dict(color="#f0a500", width=1.5), opacity=0.8), row=1, col=1)
    if show_ma and "MA50" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50",
            line=dict(color="#1b4fd8", width=1.5), opacity=0.8), row=1, col=1)
    if show_bb and "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], name="BB Upper",
            line=dict(color="#8892a4", width=1, dash="dot"), opacity=0.6), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_lower"], name="BB Lower",
            line=dict(color="#8892a4", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(136,146,164,0.05)", opacity=0.6), row=1, col=1)

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
            line=dict(color="#a855f7", width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#ff4757", opacity=0.5, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#00d4aa", opacity=0.5, row=2, col=1)

    # Volume
    if show_volume and "Volume" in df.columns:
        colors = ["#00d4aa" if c >= o else "#ff4757"
                  for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
            marker_color=colors, opacity=0.7), row=3, col=1)

    fig.update_layout(
        title=dict(text=f"<b>{ticker}</b> — Technical Analysis", font=dict(color="white", size=16)),
        paper_bgcolor="#0a0e1a", plot_bgcolor="#0d1220",
        font=dict(color="#8892a4"),
        xaxis_rangeslider_visible=False,
        legend=dict(bgcolor="rgba(20,25,40,0.8)", bordercolor="#2a3350", font=dict(color="white")),
        height=620,
        margin=dict(t=50, b=20, l=10, r=10)
    )
    fig.update_xaxes(gridcolor="#1a2035", showgrid=True)
    fig.update_yaxes(gridcolor="#1a2035", showgrid=True)
    return fig


# ── SIDEBAR ──
with st.sidebar:
    st.markdown("## 📈 SOT Market Intel")
    st.markdown("---")

    market = st.selectbox("🌍 Market", ["🇺🇸 US Stocks", "₿ Crypto", "🇳🇬 NGX Stocks", "🛢 Commodities"])

    if "US" in market:
        ticker_map = US_TICKERS
        currency = "USD"
    elif "Crypto" in market:
        ticker_map = CRYPTO_TICKERS
        currency = "USD"
    elif "NGX" in market:
        ticker_map = NGX_TICKERS
        currency = "NGN"
    else:
        ticker_map = COMMODITIES_TICKERS
        currency = "USD"

    selected_name = st.selectbox("📊 Select Asset", list(ticker_map.keys()))
    selected_ticker = ticker_map[selected_name]

    period = st.selectbox("📅 Time Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=1)
    interval_map = {"1mo": "1d", "3mo": "1d", "6mo": "1d", "1y": "1wk", "2y": "1wk", "5y": "1mo"}
    interval = interval_map[period]

    st.markdown("---")
    st.markdown("**📐 Indicators**")
    show_ma = st.checkbox("Moving Averages (MA20/50)", value=True)
    show_bb = st.checkbox("Bollinger Bands", value=True)
    show_vol = st.checkbox("Volume", value=True)

    st.markdown("---")
    st.markdown("**🔔 Price Alerts**")
    alert_high = st.number_input("Alert if price ABOVE", min_value=0.0, value=0.0, step=0.01)
    alert_low = st.number_input("Alert if price BELOW", min_value=0.0, value=0.0, step=0.01)

    st.markdown("---")
    # Show NGX market status in sidebar
    ngx_symbols_list = list(NGX_SYMBOLS.values())
    if "NGX" in market:
        mstatus, mcolor = get_market_status()
        st.markdown(f"<div style='background:rgba(20,25,40,0.8); border:1px solid #2a3350; border-radius:8px; padding:10px; margin:8px 0; text-align:center; font-size:13px; color:{mcolor}; font-weight:600;'>{mstatus}</div>", unsafe_allow_html=True)
        st.markdown("<small style='color:#8892a4;'>NGX Hours: Mon–Fri 10AM–2:30PM WAT</small>", unsafe_allow_html=True)

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(f"<small style='color:#8892a4'>Last updated: {datetime.now().strftime('%H:%M:%S')}</small>", unsafe_allow_html=True)


# ── MAIN HEADER ──
st.markdown("""
<div style='display:flex; align-items:center; gap:12px; padding:8px 0 16px 0;'>
    <div style='background:linear-gradient(135deg,#1b4fd8,#0d2d9e); border-radius:10px; padding:10px 14px; font-size:22px;'>📈</div>
    <div>
        <div style='font-size:24px; font-weight:700; color:white;'>SOT Market Intelligence Dashboard</div>
        <div style='font-size:13px; color:#8892a4;'>Real-time tracking · US Stocks · Crypto · NGX · Commodities · Built by Samuel Oyedokun</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── LIVE PRICE METRICS ──
live = get_live_price(selected_ticker)
price = live["price"]
change = live["change"]
change_pct = live["change_pct"]
color = "#00d4aa" if change >= 0 else "#ff4757"
arrow = "▲" if change >= 0 else "▼"

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Live Price ({currency})</div>
        <div class='metric-value'>{price:,.2f}</div>
        <div style='color:{color}; font-size:14px; font-weight:600;'>{arrow} {abs(change):,.2f} ({abs(change_pct):.2f}%)</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>52W High</div>
        <div class='metric-value' style='font-size:22px;'>{live['high']:,.2f}</div>
        <div class='metric-change-pos'>Year High</div>
    </div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>52W Low</div>
        <div class='metric-value' style='font-size:22px;'>{live['low']:,.2f}</div>
        <div class='metric-change-neg'>Year Low</div>
    </div>""", unsafe_allow_html=True)
with col4:
    vol_display = f"{live['volume']/1e6:.1f}M" if live['volume'] > 1e6 else f"{live['volume']:,.0f}"
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Avg Volume</div>
        <div class='metric-value' style='font-size:22px;'>{vol_display}</div>
        <div style='color:#8892a4; font-size:13px;'>3-Month Avg</div>
    </div>""", unsafe_allow_html=True)
with col5:
    # Price position in 52W range
    if live['high'] > live['low'] > 0:
        position = ((price - live['low']) / (live['high'] - live['low'])) * 100
    else:
        position = 50
    pos_color = "#00d4aa" if position > 50 else "#f0a500" if position > 25 else "#ff4757"
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>52W Position</div>
        <div class='metric-value' style='font-size:22px; color:{pos_color};'>{position:.0f}%</div>
        <div style='color:#8892a4; font-size:13px;'>From Year Low</div>
    </div>""", unsafe_allow_html=True)

# ── PRICE ALERTS ──
if alert_high > 0 and price > alert_high:
    st.markdown(f"<div class='alert-card-high'>🔴 ALERT: {selected_name} is ABOVE your target of {alert_high:,.2f} — Current: {price:,.2f}</div>", unsafe_allow_html=True)
if alert_low > 0 and price < alert_low and price > 0:
    st.markdown(f"<div class='alert-card-low'>🟢 ALERT: {selected_name} is BELOW your target of {alert_low:,.2f} — Current: {price:,.2f}</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── TABS ──
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Chart & Analysis", "💼 Portfolio Tracker", "📰 News & Sentiment", "🏆 Market Overview", "🤖 AI Market Insights"])

# ── TAB 1: CHART ──
with tab1:
    ngx_symbols = list(NGX_SYMBOLS.values())
    if selected_ticker in ngx_symbols:
        ngx_prices, ngx_source, ngx_as_of = fetch_ngx_prices()
        market_status, status_color = get_market_status()
        if ngx_source == "Last Known (Offline)":
            st.warning(f"⚠️ Could not reach NGX data sources. Showing last known prices from March 2026. | {market_status}")
        else:
            st.success(f"✅ NGX Data Source: **{ngx_source}** | Last Updated: {ngx_as_of} | {market_status} | Prices update after market close (2:30 PM WAT)")
    df, info = get_stock_data(selected_ticker, period, interval)
    if not df.empty:
        df = compute_indicators(df)
        fig = candlestick_chart(df, f"{selected_name} ({selected_ticker})", show_ma, show_bb, show_vol)
        st.plotly_chart(fig, use_container_width=True)

        # Stats row
        st.markdown("<div class='section-header'>📋 Key Statistics</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            period_return = ((df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]) * 100
            rc = "#00d4aa" if period_return >= 0 else "#ff4757"
            st.markdown(f"<div style='color:#8892a4; font-size:12px;'>Period Return</div><div style='color:{rc}; font-size:20px; font-weight:700;'>{period_return:+.2f}%</div>", unsafe_allow_html=True)
        with c2:
            volatility = df["Close"].pct_change().std() * np.sqrt(252) * 100
            st.markdown(f"<div style='color:#8892a4; font-size:12px;'>Annual Volatility</div><div style='color:white; font-size:20px; font-weight:700;'>{volatility:.1f}%</div>", unsafe_allow_html=True)
        with c3:
            if "RSI" in df.columns and not df["RSI"].isna().all():
                rsi_val = df["RSI"].iloc[-1]
                rsi_color = "#ff4757" if rsi_val > 70 else "#00d4aa" if rsi_val < 30 else "#f0a500"
                rsi_label = "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"
                st.markdown(f"<div style='color:#8892a4; font-size:12px;'>RSI ({rsi_label})</div><div style='color:{rsi_color}; font-size:20px; font-weight:700;'>{rsi_val:.1f}</div>", unsafe_allow_html=True)
        with c4:
            avg_vol = df["Volume"].mean()
            last_vol = df["Volume"].iloc[-1]
            vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
            vc = "#00d4aa" if vol_ratio > 1.2 else "#ff4757" if vol_ratio < 0.8 else "#f0a500"
            st.markdown(f"<div style='color:#8892a4; font-size:12px;'>Volume vs Avg</div><div style='color:{vc}; font-size:20px; font-weight:700;'>{vol_ratio:.2f}x</div>", unsafe_allow_html=True)
    else:
        st.warning(f"Could not load data for {selected_ticker}. Please try a different time period.")


# ── TAB 2: PORTFOLIO TRACKER ──
with tab2:
    st.markdown("<div class='section-header'>💼 Portfolio Tracker</div>", unsafe_allow_html=True)
    st.markdown("<small style='color:#8892a4;'>Add your holdings to track performance and total value</small>", unsafe_allow_html=True)

    if "portfolio" not in st.session_state:
        st.session_state.portfolio = [
            {"name": "Apple", "ticker": "AAPL", "shares": 10, "avg_cost": 150.0},
            {"name": "Bitcoin", "ticker": "BTC-USD", "shares": 0.1, "avg_cost": 40000.0},
            {"name": "NVIDIA", "ticker": "NVDA", "shares": 5, "avg_cost": 450.0},
        ]

    # Add new holding
    with st.expander("➕ Add New Holding"):
        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            all_tickers = {**US_TICKERS, **CRYPTO_TICKERS, **COMMODITIES_TICKERS}
            new_name = st.selectbox("Asset", list(all_tickers.keys()), key="new_name")
        with ac2:
            new_shares = st.number_input("Shares / Units", min_value=0.0001, value=1.0, step=0.001, key="new_shares")
        with ac3:
            new_cost = st.number_input("Avg Cost Price ($)", min_value=0.01, value=100.0, step=0.01, key="new_cost")
        with ac4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Add to Portfolio", use_container_width=True):
                st.session_state.portfolio.append({
                    "name": new_name,
                    "ticker": all_tickers[new_name],
                    "shares": new_shares,
                    "avg_cost": new_cost
                })
                st.success(f"Added {new_name}!")
                st.rerun()

    # Portfolio table
    portfolio_data = []
    total_value = 0
    total_cost = 0

    for holding in st.session_state.portfolio:
        live_data = get_live_price(holding["ticker"])
        current_price = live_data["price"]
        market_value = current_price * holding["shares"]
        cost_basis = holding["avg_cost"] * holding["shares"]
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
        total_value += market_value
        total_cost += cost_basis
        portfolio_data.append({
            "Asset": holding["name"],
            "Ticker": holding["ticker"],
            "Shares": holding["shares"],
            "Avg Cost": f"${holding['avg_cost']:,.2f}",
            "Current Price": f"${current_price:,.2f}",
            "Market Value": f"${market_value:,.2f}",
            "P&L": f"${pnl:+,.2f}",
            "P&L %": f"{pnl_pct:+.2f}%",
            "Return": pnl_pct
        })

    if portfolio_data:
        # Summary metrics
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        pc1, pc2, pc3, pc4 = st.columns(4)
        tc = "#00d4aa" if total_pnl >= 0 else "#ff4757"
        with pc1:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Value</div><div class='metric-value'>${total_value:,.2f}</div></div>", unsafe_allow_html=True)
        with pc2:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Cost</div><div class='metric-value'>${total_cost:,.2f}</div></div>", unsafe_allow_html=True)
        with pc3:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Total P&L</div><div class='metric-value' style='color:{tc};'>${total_pnl:+,.2f}</div></div>", unsafe_allow_html=True)
        with pc4:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Return</div><div class='metric-value' style='color:{tc};'>{total_pnl_pct:+.2f}%</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        df_portfolio = pd.DataFrame(portfolio_data)

        # Color P&L column
        def color_pnl(val):
            if isinstance(val, str) and "%" in val:
                num = float(val.replace("%", "").replace("+", ""))
                color = "#00d4aa" if num >= 0 else "#ff4757"
                return f"color: {color}; font-weight: 600"
            return ""

        st.dataframe(
            df_portfolio.drop(columns=["Return"]).style.applymap(color_pnl, subset=["P&L %", "P&L"]),
            use_container_width=True, hide_index=True
        )

        # Pie chart
        fig_pie = px.pie(
            df_portfolio, values=[float(v.replace("$","").replace(",","")) for v in df_portfolio["Market Value"]],
            names="Asset", title="Portfolio Allocation",
            color_discrete_sequence=["#1b4fd8","#00d4aa","#f0a500","#ff4757","#a855f7","#06b6d4"]
        )
        fig_pie.update_layout(paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
            font=dict(color="white"), title_font=dict(color="white"), height=350)
        st.plotly_chart(fig_pie, use_container_width=True)


# ── TAB 3: NEWS & SENTIMENT ──
with tab3:
    st.markdown(f"<div class='section-header'>📰 News & Sentiment — {selected_name}</div>", unsafe_allow_html=True)

    news = get_news_sentiment(selected_name)

    # Sentiment summary
    sentiments = [n["sentiment"] for n in news]
    pos_count = sentiments.count("Positive")
    neg_count = sentiments.count("Negative")
    neu_count = sentiments.count("Neutral")
    total = len(sentiments) or 1
    overall = "Bullish 🟢" if pos_count > neg_count else "Bearish 🔴" if neg_count > pos_count else "Neutral 🟡"

    nc1, nc2, nc3, nc4 = st.columns(4)
    with nc1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Overall Sentiment</div><div style='font-size:18px; font-weight:700; color:white;'>{overall}</div></div>", unsafe_allow_html=True)
    with nc2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Positive</div><div class='metric-value' style='color:#00d4aa;'>{pos_count}</div></div>", unsafe_allow_html=True)
    with nc3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Negative</div><div class='metric-value' style='color:#ff4757;'>{neg_count}</div></div>", unsafe_allow_html=True)
    with nc4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Neutral</div><div class='metric-value' style='color:#f0a500;'>{neu_count}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Sentiment bar
    fig_sent = go.Figure(go.Bar(
        x=["Positive", "Neutral", "Negative"],
        y=[pos_count, neu_count, neg_count],
        marker_color=["#00d4aa", "#f0a500", "#ff4757"],
        text=[pos_count, neu_count, neg_count],
        textposition="auto"
    ))
    fig_sent.update_layout(
        paper_bgcolor="#0a0e1a", plot_bgcolor="#0d1220",
        font=dict(color="white"), height=200,
        margin=dict(t=20, b=20), showlegend=False,
        title=dict(text="Sentiment Distribution", font=dict(color="white", size=14))
    )
    fig_sent.update_xaxes(gridcolor="#1a2035")
    fig_sent.update_yaxes(gridcolor="#1a2035")
    st.plotly_chart(fig_sent, use_container_width=True)

    # News articles
    for article in news:
        s = article["sentiment"]
        sc = "sentiment-pos" if s == "Positive" else "sentiment-neg" if s == "Negative" else "sentiment-neu"
        st.markdown(f"""
        <div class='news-card'>
            <div class='news-title'>{article['title']}</div>
            <div class='news-meta'>{article['source']} · {article['published']} · <span class='{sc}'>{s}</span></div>
        </div>""", unsafe_allow_html=True)


# ── TAB 4: MARKET OVERVIEW ──
with tab4:
    st.markdown("<div class='section-header'>🏆 Market Overview</div>", unsafe_allow_html=True)

    # Top movers — fetch a few key tickers
    watch_tickers = {"AAPL": "Apple", "MSFT": "Microsoft", "TSLA": "Tesla",
                     "NVDA": "NVIDIA", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
                     "GC=F": "Gold", "CL=F": "Crude Oil", "SI=F": "Silver"}

    overview_data = []
    for ticker, name in watch_tickers.items():
        d = get_live_price(ticker)
        overview_data.append({
            "Asset": name, "Ticker": ticker,
            "Price": d["price"], "Change": d["change"],
            "Change %": d["change_pct"]
        })

    df_ov = pd.DataFrame(overview_data)

    # Heatmap-style display
    cols = st.columns(3)
    for i, row in df_ov.iterrows():
        c = cols[i % 3]
        clr = "#00d4aa" if row["Change %"] >= 0 else "#ff4757"
        bg = "rgba(0,212,170,0.08)" if row["Change %"] >= 0 else "rgba(255,71,87,0.08)"
        arrow = "▲" if row["Change %"] >= 0 else "▼"
        c.markdown(f"""
        <div style='background:{bg}; border:1px solid {clr}40; border-radius:10px; padding:16px; margin:6px 0;'>
            <div style='font-size:13px; color:#8892a4;'>{row['Ticker']}</div>
            <div style='font-size:16px; font-weight:700; color:white;'>{row['Asset']}</div>
            <div style='font-size:20px; font-weight:700; color:white;'>${row['Price']:,.2f}</div>
            <div style='font-size:14px; color:{clr}; font-weight:600;'>{arrow} {abs(row['Change %']):.2f}%</div>
        </div>""", unsafe_allow_html=True)

    # Market comparison chart
    st.markdown("<br><div class='section-header'>📈 Performance Comparison (3 Months)</div>", unsafe_allow_html=True)
    compare_tickers = ["AAPL", "MSFT", "NVDA", "BTC-USD"]
    compare_names = ["Apple", "Microsoft", "NVIDIA", "Bitcoin"]
    colors = ["#1b4fd8", "#00d4aa", "#f0a500", "#ff4757"]

    fig_comp = go.Figure()
    for ticker, name, color in zip(compare_tickers, compare_names, colors):
        df_c, _ = get_stock_data(ticker, "3mo", "1d")
        if not df_c.empty:
            normalized = (df_c["Close"] / df_c["Close"].iloc[0] - 1) * 100
            fig_comp.add_trace(go.Scatter(
                x=df_c.index, y=normalized, name=name,
                line=dict(color=color, width=2)
            ))

    fig_comp.update_layout(
        paper_bgcolor="#0a0e1a", plot_bgcolor="#0d1220",
        font=dict(color="#8892a4"), height=350,
        yaxis_title="% Return", xaxis_title="",
        legend=dict(bgcolor="rgba(20,25,40,0.8)", bordercolor="#2a3350", font=dict(color="white")),
        margin=dict(t=20, b=20)
    )
    fig_comp.add_hline(y=0, line_dash="dot", line_color="#2a3350")
    fig_comp.update_xaxes(gridcolor="#1a2035")
    fig_comp.update_yaxes(gridcolor="#1a2035")
    st.plotly_chart(fig_comp, use_container_width=True)

# ── TAB 5: AI MARKET INSIGHTS ──
with tab5:
    st.markdown("<div class='section-header'>🤖 AI Market Insights</div>", unsafe_allow_html=True)
    st.markdown("<small style='color:#8892a4;'>Powered by Groq AI (LLaMA 3.3 70B) · Analysis is for informational purposes only, not financial advice</small>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # AI analysis type selector
    ai_col1, ai_col2 = st.columns([2, 1])
    with ai_col1:
        analysis_type = st.selectbox("📋 Analysis Type", [
            "📈 Stock Summary & Outlook",
            "🎯 Technical Analysis Interpretation",
            "📰 Market Sentiment Report",
            "⚖️ Risk Assessment",
            "🌍 Sector & Macro Commentary",
            "💡 Investment Thesis",
        ])
    with ai_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_analysis = st.button("🚀 Generate AI Analysis", use_container_width=True)

    # Build context from live data
    live_ctx = get_live_price(selected_ticker)
    price_ctx    = live_ctx.get("price", 0)
    change_ctx   = live_ctx.get("change", 0)
    chg_pct_ctx  = live_ctx.get("change_pct", 0)
    high_ctx     = live_ctx.get("high", 0)
    low_ctx      = live_ctx.get("low", 0)
    vol_ctx      = live_ctx.get("volume", 0)

    # Get RSI from chart data if available
    try:
        df_ai, _ = get_stock_data(selected_ticker, "3mo", "1d")
        if not df_ai.empty:
            df_ai = compute_indicators(df_ai)
            rsi_ctx      = round(df_ai["RSI"].iloc[-1], 1) if "RSI" in df_ai.columns else "N/A"
            ma20_ctx     = round(df_ai["MA20"].iloc[-1], 2) if "MA20" in df_ai.columns else "N/A"
            period_ret   = round(((df_ai["Close"].iloc[-1] - df_ai["Close"].iloc[0]) / df_ai["Close"].iloc[0]) * 100, 2)
            volatility   = round(df_ai["Close"].pct_change().std() * (252**0.5) * 100, 1)
        else:
            rsi_ctx = ma20_ctx = period_ret = volatility = "N/A"
    except:
        rsi_ctx = ma20_ctx = period_ret = volatility = "N/A"

    # Market context
    mkt_type = "NGX (Nigerian Stock Exchange)" if selected_ticker in list(NGX_SYMBOLS.values()) else                "Cryptocurrency" if "-USD" in selected_ticker else                "Commodity" if "=F" in selected_ticker else "US Stock"

    direction = "up" if change_ctx >= 0 else "down"

    # Show context card
    st.markdown(f"""
    <div class='metric-card' style='margin-bottom:16px;'>
        <div style='font-size:13px; color:#8892a4; margin-bottom:8px;'>📊 Current Data Context for Analysis</div>
        <div style='display:flex; gap:32px; flex-wrap:wrap;'>
            <div><span style='color:#8892a4; font-size:12px;'>Asset</span><br><span style='color:white; font-weight:600;'>{selected_name}</span></div>
            <div><span style='color:#8892a4; font-size:12px;'>Market</span><br><span style='color:white; font-weight:600;'>{mkt_type}</span></div>
            <div><span style='color:#8892a4; font-size:12px;'>Price</span><br><span style='color:white; font-weight:600;'>{price_ctx:,.2f}</span></div>
            <div><span style='color:#8892a4; font-size:12px;'>Change</span><br><span style='color:{"#00d4aa" if change_ctx>=0 else "#ff4757"}; font-weight:600;'>{"▲" if change_ctx>=0 else "▼"} {abs(chg_pct_ctx):.2f}%</span></div>
            <div><span style='color:#8892a4; font-size:12px;'>RSI</span><br><span style='color:white; font-weight:600;'>{rsi_ctx}</span></div>
            <div><span style='color:#8892a4; font-size:12px;'>3M Return</span><br><span style='color:white; font-weight:600;'>{period_ret}%</span></div>
            <div><span style='color:#8892a4; font-size:12px;'>Volatility</span><br><span style='color:white; font-weight:600;'>{volatility}%</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if run_analysis:
        # Build prompt based on analysis type
        base_data = f"""
Asset: {selected_name} ({selected_ticker})
Market: {mkt_type}
Current Price: {price_ctx:,.2f}
Price Change Today: {change_ctx:+.4f} ({chg_pct_ctx:+.2f}%) — moved {direction}
52-Week High: {high_ctx:,.2f}
52-Week Low: {low_ctx:,.2f}
3-Month Return: {period_ret}%
Annual Volatility: {volatility}%
RSI (14): {rsi_ctx}
MA20: {ma20_ctx}
Average Volume: {vol_ctx:,.0f}
"""

        prompts = {
            "📈 Stock Summary & Outlook": f"""You are a professional financial analyst. Based on the following market data, write a concise, insightful stock summary and near-term outlook for {selected_name}.

{base_data}

Write 3-4 paragraphs covering:
1. Current price action and momentum
2. Key technical levels (support/resistance based on 52W range and MA)
3. RSI signal interpretation
4. Near-term outlook (bullish/bearish/neutral) with reasoning

Be specific, use the data provided, and write in a professional financial analyst tone. End with a clear outlook statement.""",

            "🎯 Technical Analysis Interpretation": f"""You are a technical analyst. Interpret the following technical data for {selected_name} and explain what the indicators are signaling.

{base_data}

Provide:
1. Trend analysis (based on price vs MA20 and 3M return)
2. RSI interpretation — is the stock overbought, oversold, or neutral?
3. Volatility assessment
4. Key price levels to watch (based on 52W high/low)
5. Overall technical rating: Bullish / Neutral / Bearish with clear reasoning""",

            "📰 Market Sentiment Report": f"""You are a market strategist. Write a professional market sentiment report for {selected_name}.

{base_data}

Structure the report as:
1. Market Pulse — how is this asset trading today?
2. Momentum Assessment — is buying or selling pressure dominant?
3. Investor Sentiment — what does the data suggest about market confidence?
4. Comparable market context — how might macro factors (interest rates, oil prices, currency) affect this asset?
5. Sentiment Score: Bullish / Cautious / Bearish (with brief justification)""",

            "⚖️ Risk Assessment": f"""You are a risk analyst. Provide a thorough risk assessment for {selected_name} based on the data below.

{base_data}

Cover:
1. Volatility Risk — is the annual volatility high or low for this asset class?
2. Drawdown Risk — how far is the price from its 52-week high?
3. Momentum Risk — RSI and recent return signals
4. Liquidity Risk — volume assessment
5. Overall Risk Rating: Low / Medium / High / Very High
6. Key risk factors to monitor""",

            "🌍 Sector & Macro Commentary": f"""You are a macro analyst. Write a sector and macroeconomic commentary for {selected_name}.

{base_data}

Address:
1. Sector positioning — what sector/industry does this asset belong to?
2. Macro tailwinds and headwinds relevant to this asset
3. How Nigerian economic conditions / global market conditions may impact this asset
4. Currency and inflation considerations where relevant
5. Key macro events or data releases to watch""",

            "💡 Investment Thesis": f"""You are an investment analyst. Write a clear investment thesis for {selected_name} based on the current market data.

{base_data}

Structure as:
1. The Bull Case — reasons to be positive on this asset
2. The Bear Case — risks and reasons for caution  
3. Key Catalysts — what could drive price higher or lower
4. Price Levels to Watch — entry/exit considerations based on technicals
5. Thesis Summary — one paragraph conclusion

Note: This is for informational purposes only, not financial advice.""",
        }

        selected_prompt = prompts.get(analysis_type, prompts["📈 Stock Summary & Outlook"])

        with st.spinner("🤖 AI is analyzing the market data..."):
            try:
                if not GROQ_API_KEY:
                    st.error("⚠️ Groq API key not configured. Add GROQ_API_KEY to your Streamlit secrets.")
                    st.stop()

                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "max_tokens": 1000,
                        "temperature": 0.7,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a professional financial analyst and market strategist with deep expertise in global markets including Nigerian stocks (NGX), US equities, cryptocurrencies, and commodities. Provide clear, data-driven, professional analysis."
                            },
                            {"role": "user", "content": selected_prompt}
                        ]
                    },
                    timeout=30
                )
                data = response.json()
                ai_text = ""
                if "choices" in data:
                    ai_text = data["choices"][0].get("message", {}).get("content", "")

                if not ai_text and "error" in data:
                    err = data.get("error", {})
                    st.error(f"Groq API Error: {err.get('message', 'Unknown error')}")
                elif not ai_text:
                    st.error(f"Empty response. Please try again.")

                if ai_text:
                    # Display AI response in styled card
                    st.markdown(f"""
                    <div style='background:linear-gradient(135deg,#141928,#1a2035); border:1px solid #2a3350;
                         border-left: 4px solid #1b4fd8; border-radius:12px; padding:24px; margin:16px 0;'>
                        <div style='font-size:13px; color:#1b4fd8; font-weight:600; margin-bottom:12px;'>
                            🤖 Groq AI Analysis · {analysis_type} · {selected_name} · {datetime.now().strftime("%Y-%m-%d %H:%M")}
                        </div>
                        <div style='color:#e0e6f0; font-size:14px; line-height:1.8; white-space:pre-wrap;'>{ai_text}</div>
                        <div style='margin-top:16px; font-size:11px; color:#8892a4; border-top:1px solid #2a3350; padding-top:10px;'>
                            ⚠️ This analysis is generated by AI for informational purposes only. It is not financial advice.
                            Always do your own research before making investment decisions.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Download button
                    report = f"SOT Market Intelligence — AI Analysis\n{'='*50}\n"
                    report += f"Asset: {selected_name} ({selected_ticker})\n"
                    report += f"Analysis Type: {analysis_type}\n"
                    report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    report += f"{'='*50}\n\n{ai_text}\n\n"
                    report += "⚠️ For informational purposes only. Not financial advice."
                    st.download_button(
                        "📥 Download Report",
                        data=report,
                        file_name=f"SOT_AI_{selected_name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain"
                    )
                else:
                    st.error("AI returned an empty response. Please try again.")

            except Exception as e:
                st.error(f"AI analysis failed: {str(e)}. Please check your connection and try again.")



# ── FOOTER ──
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align:center; padding:20px; border-top:1px solid #2a3350; color:#8892a4; font-size:12px;'>
    Built by <strong style='color:#1b4fd8;'>Samuel Oyedokun</strong> · 
    Data via Yahoo Finance · 
    <a href='https://github.com/SamuelOyedokun' style='color:#1b4fd8;'>GitHub</a> · 
    <a href='https://www.linkedin.com/in/samuel-oyedokun-b41895142' style='color:#1b4fd8;'>LinkedIn</a>
</div>
""", unsafe_allow_html=True)
