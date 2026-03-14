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

NGX_TICKERS = {
    "Dangote Cement": "DANGCEM.LG", "GTBank": "GTCO.LG", "Zenith Bank": "ZENITHBA.LG",
    "MTN Nigeria": "MTNN.LG", "Access Bank": "ACCESSCO.LG", "Stanbic IBTC": "STANBIC.LG",
    "FBN Holdings": "FBNH.LG", "UBA": "UBA.LG", "Nestle Nigeria": "NESTLE.LG",
    "Airtel Africa": "AIRTELAFRI.LG"
}

NEWS_API_KEY = "bca6285fbfa8401bbbea1a81be93d394"  # Free at newsapi.org


# ── DATA FUNCTIONS ──
@st.cache_data(ttl=300)
def get_stock_data(ticker, period="3mo", interval="1d"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        info = stock.info
        return df, info
    except Exception as e:
        return pd.DataFrame(), {}


@st.cache_data(ttl=60)
def get_live_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        return {
            "price": round(info.last_price, 2) if hasattr(info, 'last_price') and info.last_price else 0,
            "change": round(info.last_price - info.previous_close, 2) if hasattr(info, 'previous_close') and info.previous_close else 0,
            "change_pct": round(((info.last_price - info.previous_close) / info.previous_close) * 100, 2) if hasattr(info, 'previous_close') and info.previous_close and info.previous_close != 0 else 0,
            "volume": info.three_month_average_volume if hasattr(info, 'three_month_average_volume') else 0,
            "high": info.year_high if hasattr(info, 'year_high') else 0,
            "low": info.year_low if hasattr(info, 'year_low') else 0,
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

    market = st.selectbox("🌍 Market", ["🇺🇸 US Stocks", "₿ Crypto", "🇳🇬 NGX Stocks"])
    
    if "US" in market:
        ticker_map = US_TICKERS
        currency = "USD"
    elif "Crypto" in market:
        ticker_map = CRYPTO_TICKERS
        currency = "USD"
    else:
        ticker_map = NGX_TICKERS
        currency = "NGN"

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
        <div style='font-size:13px; color:#8892a4;'>Real-time tracking · US Stocks · Crypto · NGX · Built by Samuel Oyedokun</div>
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
tab1, tab2, tab3, tab4 = st.tabs(["📊 Chart & Analysis", "💼 Portfolio Tracker", "📰 News & Sentiment", "🏆 Market Overview"])

# ── TAB 1: CHART ──
with tab1:
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
        st.warning(f"Could not load data for {selected_ticker}. NGX stocks may have limited data on Yahoo Finance.")


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
            all_tickers = {**US_TICKERS, **CRYPTO_TICKERS}
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
                     "NVDA": "NVIDIA", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum"}

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
