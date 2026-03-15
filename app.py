import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
import requests
import json
from datetime import datetime, timedelta
import time
# ── GROQ AI CONFIG (Free) ──
try:
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
except:
    import os
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── EMAIL ALERT FUNCTION ──
def send_email_alert(to_email, subject, asset_name, ticker, alert_type, alert_price, current_price, sender_email, sender_password):
    """Send price alert email via Gmail SMTP"""
    try:
        direction = "risen ABOVE" if alert_type == "high" else "fallen BELOW"
        arrow     = "🔴" if alert_type == "high" else "🟢"
        color     = "#ff4757" if alert_type == "high" else "#00d4aa"
        action    = "Consider reviewing your position." if alert_type == "high" else "This may be a buying opportunity."

        html = f"""
        <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto; background:#0a0e1a; padding:32px; border-radius:12px;">
            <div style="text-align:center; margin-bottom:24px;">
                <div style="font-size:40px;">{arrow}</div>
                <h1 style="color:white; font-size:22px; margin:8px 0;">Price Alert Triggered</h1>
                <p style="color:#8892a4; font-size:14px; margin:0;">SOT Market Intelligence Dashboard</p>
            </div>
            <div style="background:#141928; border:1px solid #2a3350; border-radius:10px; padding:24px; margin-bottom:20px;">
                <h2 style="color:white; font-size:18px; margin:0 0 16px 0;">{asset_name} ({ticker})</h2>
                <p style="color:#8892a4; font-size:14px; margin:0 0 8px 0;">The price has <strong style="color:{color};">{direction}</strong> your alert level.</p>
                <table style="width:100%; border-collapse:collapse; margin-top:16px;">
                    <tr>
                        <td style="color:#8892a4; font-size:13px; padding:8px 0;">Your Alert Level</td>
                        <td style="color:white; font-size:16px; font-weight:700; text-align:right;">${alert_price:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="color:#8892a4; font-size:13px; padding:8px 0;">Current Price</td>
                        <td style="color:{color}; font-size:20px; font-weight:700; text-align:right;">${current_price:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="color:#8892a4; font-size:13px; padding:8px 0;">Difference</td>
                        <td style="color:{color}; font-size:14px; font-weight:600; text-align:right;">${abs(current_price - alert_price):,.2f} ({abs((current_price - alert_price)/alert_price*100):.2f}%)</td>
                    </tr>
                </table>
            </div>
            <p style="color:#8892a4; font-size:13px; text-align:center;">{action}</p>
            <p style="color:#555; font-size:11px; text-align:center; margin-top:24px; border-top:1px solid #2a3350; padding-top:16px;">
                This alert was sent by SOT Market Intelligence Dashboard.<br>
                ⚠️ For informational purposes only. Not financial advice.<br>
                Alert triggered at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} WAT
            </p>
        </div>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{arrow} {subject}"
        msg["From"]    = sender_email
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        return True, "Email sent successfully"
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail authentication failed. Use an App Password, not your regular password."
    except Exception as e:
        return False, str(e)

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

# ── NEWS API KEY (from Streamlit secrets) ──
try:
    NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", "")
except:
    import os
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")


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


# ── RSS FEED SOURCES ──
RSS_FEEDS = {
    "Reuters Business":    "https://feeds.reuters.com/reuters/businessNews",
    "BBC Business":        "http://feeds.bbci.co.uk/news/business/rss.xml",
    "MarketWatch":         "https://feeds.marketwatch.com/marketwatch/topstories",
    "Yahoo Finance":       "https://finance.yahoo.com/news/rssindex",
    "Nairametrics":        "https://nairametrics.com/feed/",
    "BusinessDay Nigeria": "https://businessday.ng/feed/",
}

def _keyword_sentiment(text):
    """Finance-specific keyword sentiment scoring"""
    pos = ["surge","rally","gain","rise","bull","profit","growth","beat","high",
           "strong","record","breakthrough","upgrade","buy","outperform","boost",
           "revenue","earnings beat","raised guidance","dividend","acquisition",
           "partnership","launch","approval","expansion","recovery","rebound"]
    neg = ["crash","fall","drop","bear","loss","down","decline","miss","risk",
           "weak","cut","downgrade","sell","concern","warning","slump","recall",
           "investigation","lawsuit","fine","penalty","layoff","bankruptcy",
           "missed expectations","lowered guidance","debt","fraud","scandal"]
    # Irrelevant signals — if only these match, mark neutral
    irrelevant = ["recipe","festival","concert","sports","weather","celebrity",
                  "entertainment","movie","music","food","travel","fashion"]
    t  = text.lower()
    if any(w in t for w in irrelevant) and not any(w in t for w in pos + neg):
        return "Neutral"
    ps = sum(1 for w in pos if w in t)
    ns = sum(1 for w in neg if w in t)
    if ps > ns:   return "Positive"
    elif ns > ps: return "Negative"
    return "Neutral"

def _ai_sentiment_batch(articles, groq_key):
    """Use Groq AI to score sentiment for a batch of headlines"""
    if not groq_key or not articles:
        return None
    try:
        headlines = "\n".join([f"{i+1}. {a['title']}" for i, a in enumerate(articles)])
        prompt = f"""You are a financial market analyst. For each headline below, score the sentiment specifically for {query} as a publicly traded asset.

Rules:
- "Positive" = headline suggests {query} stock price will go UP (earnings beat, upgrade, buyback, strong revenue, partnerships, new market entry)
- "Negative" = headline suggests {query} stock price will go DOWN (earnings miss, downgrade, legal trouble, revenue decline, CEO departure, competition threat)
- "Neutral"  = product reviews, tech deals, accessories, or headlines with no clear stock price impact

IMPORTANT: Product deals, discounts, gadget reviews, and accessory news = "Neutral" (not stock-relevant).
Only executive departures, financial results, analyst ratings, and major business events affect stock price.

Return ONLY a JSON array in the same order, e.g. ["Positive","Negative","Neutral"].
No explanation, no markdown, just the JSON array.

Asset: {query}
Headlines:
{headlines}"""
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "max_tokens": 200, "temperature": 0,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=15
        )
        raw  = r.json()["choices"][0]["message"]["content"].strip()
        raw  = raw.replace("```json","").replace("```","").strip()
        scores = json.loads(raw)
        if isinstance(scores, list) and len(scores) == len(articles):
            return scores
    except:
        pass
    return None

def _fetch_rss(feed_url, query, max_items=5):
    """Fetch and filter RSS feed articles matching query"""
    results = []
    try:
        hdrs = {"User-Agent": "Mozilla/5.0 (compatible; SOTDashboard/1.0)"}
        r    = requests.get(feed_url, headers=hdrs, timeout=8)
        if r.status_code != 200:
            return []
        from xml.etree import ElementTree as ET
        root  = ET.fromstring(r.content)
        items = root.findall(".//item")
        query_terms = query.lower().split()
        for item in items:
            title   = (item.findtext("title")       or "").strip()
            link    = (item.findtext("link")         or "#").strip()
            pubdate = (item.findtext("pubDate")      or "").strip()
            desc    = (item.findtext("description")  or "").strip()
            combined = (title + " " + desc).lower()
            # Require the main asset name to appear (not just any term)
            main_term = query_terms[0] if query_terms else ""
            if main_term and main_term in combined:
                # Parse date
                try:
                    from email.utils import parsedate_to_datetime
                    pub = parsedate_to_datetime(pubdate).strftime("%Y-%m-%d")
                except:
                    pub = datetime.now().strftime("%Y-%m-%d")
                # Strip HTML tags from description
                clean_desc = re.sub(r'<[^>]+>', '', desc).strip()
                clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
                results.append({
                    "title":     title,
                    "url":       link,
                    "published": pub,
                    "source":    "",   # filled by caller
                    "sentiment": "",   # filled later
                    "desc":      clean_desc[:200],
                })
                if len(results) >= max_items:
                    break
    except:
        pass
    return results

def get_news_sentiment(query, ticker="", groq_key=""):  # No cache — Groq key must be fresh each call
    """
    Multi-source news + AI sentiment:
    1. NewsAPI (if key available)
    2. RSS feeds (Reuters, BBC, MarketWatch, Yahoo Finance, Nairametrics, BusinessDay)
    3. AI sentiment scoring via Groq
    4. Keyword fallback if AI unavailable
    """
    articles = []

    # Source 1: NewsAPI — finance-specific query to reduce irrelevant articles
    if NEWS_API_KEY:
        try:
            # Build a focused financial query
            ticker_part  = query  # e.g. "Apple" or "DANGCEM"
            finance_query = f'"{ticker_part}" AND (stock OR shares OR earnings OR "stock price" OR investor OR revenue OR profit OR "market cap" OR analyst OR "Wall Street" OR NSE OR NGX)'
            url = (
                f"https://newsapi.org/v2/everything"
                f"?q={requests.utils.quote(finance_query)}"
                f"&sortBy=publishedAt&pageSize=15&language=en"
                f"&domains=reuters.com,bloomberg.com,cnbc.com,wsj.com,ft.com,"
                f"businessday.ng,nairametrics.com,techcrunch.com,forbes.com,marketwatch.com"
                f"&apiKey={NEWS_API_KEY}"
            )
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                raw_articles = r.json().get("articles", [])
                query_lower  = ticker_part.lower()
                for a in raw_articles:
                    title = (a.get("title") or "").strip()
                    desc  = (a.get("description") or "").strip()
                    if not title or title == "[Removed]":
                        continue
                    # Relevance filter: title or desc must mention the asset
                    combined = (title + " " + desc).lower()
                    if query_lower not in combined:
                        continue
                    clean_desc = re.sub(r'<[^>]+>', '', desc).strip()
                    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
                    articles.append({
                        "title":     title,
                        "url":       a.get("url", "#"),
                        "published": (a.get("publishedAt") or "")[:10],
                        "source":    a.get("source", {}).get("name", "NewsAPI"),
                        "sentiment": "",
                        "desc":      clean_desc[:200],
                    })
                    if len(articles) >= 8:
                        break
        except:
            pass

    # Source 2: RSS feeds
    for feed_name, feed_url in RSS_FEEDS.items():
        rss_items = _fetch_rss(feed_url, query, max_items=3)
        for item in rss_items:
            item["source"] = feed_name
            articles.append(item)
        if len(articles) >= 15:
            break

    # Deduplicate by title similarity
    seen   = set()
    unique = []
    for a in articles:
        key = a["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)
    articles = unique[:12]

    if not articles:
        # Final fallback — clearly labeled as demo
        return [
            {"title": f"{query}: No live news available — configure NewsAPI key for real articles", "source": "Demo", "url": "#", "published": datetime.now().strftime("%Y-%m-%d"), "sentiment": "Neutral", "desc": ""},
        ]

    # Score sentiment — try AI first, fall back to keywords
    ai_scores = _ai_sentiment_batch(articles, groq_key) if groq_key else None
    for i, article in enumerate(articles):
        if ai_scores and i < len(ai_scores) and ai_scores[i] in ("Positive","Negative","Neutral"):
            article["sentiment"] = ai_scores[i]
            article["scored_by"] = "AI"
        else:
            article["sentiment"] = _keyword_sentiment(article["title"] + " " + article.get("desc",""))
            article["scored_by"] = "Keywords"

    return articles


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

    # Initialise alerts state
    if "alerts" not in st.session_state:
        st.session_state.alerts = []  # [{name, ticker, type, level, email, active, triggered}]
    if "alert_email_sender" not in st.session_state:
        st.session_state.alert_email_sender = ""
    if "alert_email_password" not in st.session_state:
        st.session_state.alert_email_password = ""

    # Quick alert setup
    alert_high = st.number_input("🔴 Alert ABOVE", min_value=0.0, value=0.0, step=0.01, key="alert_high_input")
    alert_low  = st.number_input("🟢 Alert BELOW", min_value=0.0, value=0.0, step=0.01, key="alert_low_input")
    alert_email_quick = st.text_input("📧 Alert Email", placeholder="your@email.com", key="alert_email_quick")

    if st.button("➕ Set Alert", use_container_width=True, key="set_alert_btn"):
        if not alert_email_quick:
            st.error("Enter your email first")
        elif alert_high <= 0 and alert_low <= 0:
            st.error("Set at least one price level")
        else:
            if alert_high > 0:
                st.session_state.alerts.append({
                    "id": len(st.session_state.alerts),
                    "name": selected_name, "ticker": selected_ticker,
                    "type": "high", "level": alert_high,
                    "email": alert_email_quick, "active": True, "triggered": False
                })
            if alert_low > 0:
                st.session_state.alerts.append({
                    "id": len(st.session_state.alerts),
                    "name": selected_name, "ticker": selected_ticker,
                    "type": "low", "level": alert_low,
                    "email": alert_email_quick, "active": True, "triggered": False
                })
            st.success(f"Alert set for {selected_name}!")

    alert_high = st.session_state.get("alert_high_input", 0.0)
    alert_low  = st.session_state.get("alert_low_input",  0.0)

    st.markdown("---")
    # Show NGX market status in sidebar
    ngx_symbols_list = list(NGX_SYMBOLS.values())
    if "NGX" in market:
        mstatus, mcolor = get_market_status()
        st.markdown(f"<div style='background:rgba(20,25,40,0.8); border:1px solid #2a3350; border-radius:8px; padding:10px; margin:8px 0; text-align:center; font-size:13px; color:{mcolor}; font-weight:600;'>{mstatus}</div>", unsafe_allow_html=True)
        st.markdown("<small style='color:#8892a4;'>NGX Hours: Mon–Fri 10AM–2:30PM WAT</small>", unsafe_allow_html=True)

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        # Clear news cache specifically to re-trigger AI scoring
        get_news_sentiment.clear()
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

# ── LIVE ALERT CHECKER (auto-runs every page refresh) ──
def check_and_fire_alerts(alerts, sender_email, sender_password):
    fired = []
    for alert in alerts:
        if not alert.get("active") or alert.get("triggered"):
            continue
        live = get_live_price(alert["ticker"])
        cp   = live.get("price", 0)
        if cp <= 0:
            continue
        triggered = (alert["type"] == "high" and cp > alert["level"]) or                     (alert["type"] == "low"  and cp < alert["level"])
        if triggered:
            alert["triggered"] = True
            alert["active"]    = False
            fired.append((alert, cp))
            if sender_email and sender_password:
                direction = "risen above" if alert["type"] == "high" else "fallen below"
                send_email_alert(
                    to_email       = alert["email"],
                    subject        = f"{alert['name']} has {direction} ${alert['level']:,.2f}",
                    asset_name     = alert["name"],
                    ticker         = alert["ticker"],
                    alert_type     = alert["type"],
                    alert_price    = alert["level"],
                    current_price  = cp,
                    sender_email   = sender_email,
                    sender_password= sender_password,
                )
    return fired

# Auto-check all active alerts on every page load
if "alerts" in st.session_state and st.session_state.alerts:
    try:
        _sender_email = st.secrets.get("ALERT_SENDER_EMAIL", "")
        _sender_pass  = st.secrets.get("ALERT_SENDER_PASSWORD", "")
    except:
        _sender_email = ""
        _sender_pass  = ""

    _fired = check_and_fire_alerts(
        st.session_state.alerts, _sender_email, _sender_pass
    )
    for _alert, _cp in _fired:
        _arrow = "🔴" if _alert["type"] == "high" else "🟢"
        _dir   = "ABOVE" if _alert["type"] == "high" else "BELOW"
        st.markdown(f"<div class='alert-card-{'high' if _alert['type']=='high' else 'low'}'>{_arrow} ALERT TRIGGERED: <strong>{_alert['name']}</strong> is {_dir} ${_alert['level']:,.2f} — Current: ${_cp:,.2f} {'📧 Email sent!' if _sender_email else '(Add ALERT_SENDER_EMAIL to secrets to enable emails)'}</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── TABS ──
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Chart & Analysis", "💼 Portfolio Tracker", "📰 News & Sentiment", "🏆 Market Overview", "🤖 AI Market Insights", "🔔 Price Alerts"])

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
    st.markdown("<div class='section-header'>💼 Portfolio Simulator</div>", unsafe_allow_html=True)
    st.markdown("<small style='color:#8892a4;'>Simulate buy/sell trades with virtual money · Track real P&L with live prices · All markets supported</small>", unsafe_allow_html=True)

    # ── INITIALISE SESSION STATE ──
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = []   # [{name, ticker, shares, avg_cost, market}]
    if "trade_history" not in st.session_state:
        st.session_state.trade_history = []  # [{date, action, name, ticker, shares, price, total}]
    if "cash_balance" not in st.session_state:
        st.session_state.cash_balance = 10000.0  # Starting virtual cash

    all_tickers_map = {**US_TICKERS, **CRYPTO_TICKERS, **COMMODITIES_TICKERS, **{n: s for n, s in NGX_SYMBOLS.items()}}

    # ── CASH BALANCE BAR ──
    total_invested = sum(
        get_live_price(h["ticker"]).get("price", 0) * h["shares"]
        for h in st.session_state.portfolio
    )
    total_account = st.session_state.cash_balance + total_invested

    cb1, cb2, cb3, cb4 = st.columns(4)
    with cb1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>💵 Cash Balance</div>
            <div class='metric-value' style='font-size:22px;'>${st.session_state.cash_balance:,.2f}</div>
            <div style='color:#8892a4; font-size:12px;'>Available to invest</div>
        </div>""", unsafe_allow_html=True)
    with cb2:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>📊 Invested Value</div>
            <div class='metric-value' style='font-size:22px;'>${total_invested:,.2f}</div>
            <div style='color:#8892a4; font-size:12px;'>Live market value</div>
        </div>""", unsafe_allow_html=True)
    with cb3:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>🏦 Total Account</div>
            <div class='metric-value' style='font-size:22px;'>${total_account:,.2f}</div>
            <div style='color:#8892a4; font-size:12px;'>Cash + Investments</div>
        </div>""", unsafe_allow_html=True)
    with cb4:
        overall_pnl = total_account - 10000.0
        oc = "#00d4aa" if overall_pnl >= 0 else "#ff4757"
        overall_pct = (overall_pnl / 10000.0) * 100
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>📈 Total Return</div>
            <div class='metric-value' style='font-size:22px; color:{oc};'>{overall_pct:+.2f}%</div>
            <div style='color:{oc}; font-size:12px; font-weight:600;'>${overall_pnl:+,.2f} from $10,000</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── BUY / SELL PANEL ──
    trade_tab1, trade_tab2, trade_tab3 = st.tabs(["🟢 Buy", "🔴 Sell", "📋 Trade History"])

    with trade_tab1:
        st.markdown("#### 🟢 Place a Buy Order")
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            buy_name = st.selectbox("Asset", list(all_tickers_map.keys()), key="buy_name")
        with b2:
            buy_ticker = all_tickers_map[buy_name]
            buy_live   = get_live_price(buy_ticker)
            buy_price  = buy_live.get("price", 0)
            st.markdown(f"<div style='padding:8px 0;'><span style='color:#8892a4; font-size:12px;'>LIVE PRICE</span><br><span style='color:#00d4aa; font-size:20px; font-weight:700;'>${buy_price:,.2f}</span></div>", unsafe_allow_html=True)
        with b3:
            buy_shares = st.number_input("Qty / Units", min_value=0.0001, value=1.0, step=0.001, key="buy_shares")
        with b4:
            buy_total  = buy_price * buy_shares
            st.markdown(f"<div style='padding:8px 0;'><span style='color:#8892a4; font-size:12px;'>ORDER TOTAL</span><br><span style='color:white; font-size:20px; font-weight:700;'>${buy_total:,.2f}</span></div>", unsafe_allow_html=True)

        if st.button("✅ Execute Buy Order", use_container_width=True, key="exec_buy"):
            if buy_price <= 0:
                st.error("Cannot fetch live price. Try again.")
            elif buy_total > st.session_state.cash_balance:
                st.error(f"Insufficient cash. You need ${buy_total:,.2f} but have ${st.session_state.cash_balance:,.2f}")
            else:
                # Deduct cash
                st.session_state.cash_balance -= buy_total
                # Update or add holding
                existing = next((h for h in st.session_state.portfolio if h["ticker"] == buy_ticker), None)
                if existing:
                    total_shares = existing["shares"] + buy_shares
                    existing["avg_cost"] = ((existing["avg_cost"] * existing["shares"]) + buy_total) / total_shares
                    existing["shares"]   = total_shares
                else:
                    st.session_state.portfolio.append({
                        "name": buy_name, "ticker": buy_ticker,
                        "shares": buy_shares, "avg_cost": buy_price,
                    })
                # Log trade
                st.session_state.trade_history.append({
                    "Date":   datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Action": "🟢 BUY",
                    "Asset":  buy_name,
                    "Ticker": buy_ticker,
                    "Qty":    buy_shares,
                    "Price":  buy_price,
                    "Total":  buy_total,
                })
                st.success(f"✅ Bought {buy_shares:.4f} × {buy_name} @ ${buy_price:,.2f} | Total: ${buy_total:,.2f}")
                st.rerun()

    with trade_tab2:
        st.markdown("#### 🔴 Place a Sell Order")
        if not st.session_state.portfolio:
            st.info("No holdings to sell. Buy something first.")
        else:
            s1, s2, s3, s4 = st.columns(4)
            holding_names = [h["name"] for h in st.session_state.portfolio]
            with s1:
                sell_name    = st.selectbox("Holding", holding_names, key="sell_name")
            holding_data     = next(h for h in st.session_state.portfolio if h["name"] == sell_name)
            sell_ticker      = holding_data["ticker"]
            sell_live        = get_live_price(sell_ticker)
            sell_price       = sell_live.get("price", 0)
            with s2:
                st.markdown(f"<div style='padding:8px 0;'><span style='color:#8892a4; font-size:12px;'>LIVE PRICE</span><br><span style='color:#ff4757; font-size:20px; font-weight:700;'>${sell_price:,.2f}</span></div>", unsafe_allow_html=True)
            with s3:
                sell_qty = st.number_input("Qty to Sell", min_value=0.0001,
                    max_value=float(holding_data["shares"]),
                    value=float(holding_data["shares"]), step=0.001, key="sell_qty")
            with s4:
                sell_total = sell_price * sell_qty
                sell_pnl   = (sell_price - holding_data["avg_cost"]) * sell_qty
                pnl_color  = "#00d4aa" if sell_pnl >= 0 else "#ff4757"
                st.markdown(f"<div style='padding:8px 0;'><span style='color:#8892a4; font-size:12px;'>PROCEEDS · P&L</span><br><span style='color:white; font-size:16px; font-weight:700;'>${sell_total:,.2f}</span><span style='color:{pnl_color}; font-size:14px; font-weight:600; margin-left:8px;'>{sell_pnl:+,.2f}</span></div>", unsafe_allow_html=True)

            # Show holding info
            st.markdown(f"<small style='color:#8892a4;'>You hold {holding_data['shares']:.4f} units · Avg cost: ${holding_data['avg_cost']:,.2f}</small>", unsafe_allow_html=True)

            if st.button("✅ Execute Sell Order", use_container_width=True, key="exec_sell"):
                if sell_price <= 0:
                    st.error("Cannot fetch live price. Try again.")
                elif sell_qty > holding_data["shares"]:
                    st.error("Cannot sell more than you hold.")
                else:
                    st.session_state.cash_balance += sell_total
                    holding_data["shares"] -= sell_qty
                    if holding_data["shares"] < 0.0001:
                        st.session_state.portfolio = [h for h in st.session_state.portfolio if h["ticker"] != sell_ticker]
                    st.session_state.trade_history.append({
                        "Date":   datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Action": "🔴 SELL",
                        "Asset":  sell_name,
                        "Ticker": sell_ticker,
                        "Qty":    sell_qty,
                        "Price":  sell_price,
                        "Total":  sell_total,
                    })
                    arrow = "▲" if sell_pnl >= 0 else "▼"
                    st.success(f"✅ Sold {sell_qty:.4f} × {sell_name} @ ${sell_price:,.2f} | P&L: {arrow} ${abs(sell_pnl):,.2f}")
                    st.rerun()

    with trade_tab3:
        st.markdown("#### 📋 Trade History")
        if not st.session_state.trade_history:
            st.info("No trades yet. Place a buy or sell order to get started.")
        else:
            df_hist = pd.DataFrame(st.session_state.trade_history)
            df_hist["Price"] = df_hist["Price"].apply(lambda x: f"${x:,.2f}")
            df_hist["Total"] = df_hist["Total"].apply(lambda x: f"${x:,.2f}")
            df_hist["Qty"]   = df_hist["Qty"].apply(lambda x: f"{x:.4f}")
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            if st.button("🗑️ Clear Trade History", key="clear_hist"):
                st.session_state.trade_history = []
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── HOLDINGS TABLE ──
    if st.session_state.portfolio:
        st.markdown("<div class='section-header'>📊 Current Holdings</div>", unsafe_allow_html=True)

        portfolio_data = []
        total_value    = 0
        total_cost     = 0

        for holding in st.session_state.portfolio:
            live_data     = get_live_price(holding["ticker"])
            current_price = live_data["price"]
            market_value  = current_price * holding["shares"]
            cost_basis    = holding["avg_cost"] * holding["shares"]
            pnl           = market_value - cost_basis
            pnl_pct       = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            weight        = 0  # will calculate after
            total_value  += market_value
            total_cost   += cost_basis
            portfolio_data.append({
                "Asset":         holding["name"],
                "Ticker":        holding["ticker"],
                "Qty":           holding["shares"],
                "Avg Cost":      f"${holding['avg_cost']:,.2f}",
                "Live Price":    f"${current_price:,.2f}",
                "Market Value":  market_value,
                "P&L ($)":       pnl,
                "P&L (%)":       pnl_pct,
            })

        total_pnl     = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        tc = "#00d4aa" if total_pnl >= 0 else "#ff4757"

        # Summary row
        ph1, ph2, ph3, ph4 = st.columns(4)
        with ph1:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Portfolio Value</div><div class='metric-value'>${total_value:,.2f}</div></div>", unsafe_allow_html=True)
        with ph2:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Invested</div><div class='metric-value'>${total_cost:,.2f}</div></div>", unsafe_allow_html=True)
        with ph3:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Unrealised P&L</div><div class='metric-value' style='color:{tc};'>${total_pnl:+,.2f}</div></div>", unsafe_allow_html=True)
        with ph4:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Portfolio Return</div><div class='metric-value' style='color:{tc};'>{total_pnl_pct:+.2f}%</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Format table
        df_port = pd.DataFrame(portfolio_data)
        df_port["Weight"] = df_port["Market Value"].apply(lambda x: f"{(x/total_value*100):.1f}%" if total_value > 0 else "0%")
        df_port["P&L ($)"] = df_port["P&L ($)"].apply(lambda x: f"${x:+,.2f}")
        df_port["P&L (%)"] = df_port["P&L (%)"].apply(lambda x: f"{x:+.2f}%")
        df_port["Market Value"] = df_port["Market Value"].apply(lambda x: f"${x:,.2f}")
        df_port["Qty"] = df_port["Qty"].apply(lambda x: f"{x:.4f}")

        def color_pnl(val):
            if isinstance(val, str) and ("+" in val or (val.startswith("-") and any(c.isdigit() for c in val))):
                try:
                    num = float(val.replace("$","").replace("%","").replace("+","").replace(",",""))
                    color = "#00d4aa" if num >= 0 else "#ff4757"
                    return f"color: {color}; font-weight: 600"
                except: pass
            return ""

        st.dataframe(
            df_port.style.applymap(color_pnl, subset=["P&L ($)", "P&L (%)"]),
            use_container_width=True, hide_index=True
        )

        # ── CHARTS ──
        st.markdown("<br>", unsafe_allow_html=True)
        chart_c1, chart_c2 = st.columns(2)

        raw_values = [float(h["shares"] * get_live_price(h["ticker"]).get("price", 0)) for h in st.session_state.portfolio]
        raw_names  = [h["name"] for h in st.session_state.portfolio]

        with chart_c1:
            fig_pie = px.pie(
                values=raw_values, names=raw_names,
                title="Portfolio Allocation",
                color_discrete_sequence=["#1b4fd8","#00d4aa","#f0a500","#ff4757","#a855f7","#06b6d4","#ec4899","#14b8a6"]
            )
            fig_pie.update_traces(textinfo="label+percent", hole=0.4)
            fig_pie.update_layout(
                paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
                font=dict(color="white"), title_font=dict(color="white"),
                height=350, showlegend=False,
                annotations=[dict(text="Portfolio", x=0.5, y=0.5, font_size=13, showarrow=False, font_color="white")]
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with chart_c2:
            pnl_vals  = [float(h["shares"] * get_live_price(h["ticker"]).get("price",0)) - float(h["shares"] * h["avg_cost"]) for h in st.session_state.portfolio]
            pnl_names = [h["name"] for h in st.session_state.portfolio]
            pnl_colors = ["#00d4aa" if v >= 0 else "#ff4757" for v in pnl_vals]
            fig_pnl = go.Figure(go.Bar(
                x=pnl_names, y=pnl_vals,
                marker_color=pnl_colors,
                text=[f"${v:+,.0f}" for v in pnl_vals],
                textposition="auto"
            ))
            fig_pnl.update_layout(
                title="P&L by Holding",
                paper_bgcolor="#0a0e1a", plot_bgcolor="#0d1220",
                font=dict(color="white"), title_font=dict(color="white"),
                height=350, showlegend=False,
                margin=dict(t=40, b=20)
            )
            fig_pnl.add_hline(y=0, line_dash="dot", line_color="#2a3350")
            fig_pnl.update_xaxes(gridcolor="#1a2035")
            fig_pnl.update_yaxes(gridcolor="#1a2035")
            st.plotly_chart(fig_pnl, use_container_width=True)

        # ── RESET BUTTON ──
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Reset Portfolio (Start Fresh with $10,000)", key="reset_portfolio"):
            st.session_state.portfolio     = []
            st.session_state.trade_history = []
            st.session_state.cash_balance  = 10000.0
            st.success("Portfolio reset! Starting fresh with $10,000.")
            st.rerun()

    else:
        st.markdown("""
        <div style='background:#141928; border:1px solid #2a3350; border-radius:12px;
             padding:40px; text-align:center; margin:20px 0;'>
            <div style='font-size:36px; margin-bottom:12px;'>💼</div>
            <div style='font-size:18px; font-weight:600; color:white; margin-bottom:8px;'>No Holdings Yet</div>
            <div style='color:#8892a4; font-size:14px;'>Use the 🟢 Buy tab above to simulate your first investment.</div>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 3: NEWS & SENTIMENT ──
with tab3:
    st.markdown(f"<div class='section-header'>📰 News & Sentiment — {selected_name}</div>", unsafe_allow_html=True)

    # Fetch news with Groq AI scoring — uses global GROQ_API_KEY loaded at startup
    with st.spinner("🔍 Fetching news from multiple sources..."):
        news = get_news_sentiment(selected_name, selected_ticker, GROQ_API_KEY)

    # Data sources info
    sources_used = list(set(a["source"] for a in news if a.get("source")))
    ai_scored    = sum(1 for a in news if a.get("scored_by") == "AI")
    st.markdown(f"""
    <div style='background:#141928; border:1px solid #2a3350; border-radius:8px;
         padding:10px 16px; margin-bottom:16px; font-size:12px; color:#8892a4;'>
        📡 <strong style='color:white;'>Sources:</strong> {", ".join(sources_used) if sources_used else "Demo"} &nbsp;·&nbsp;
        🤖 <strong style='color:white;'>{ai_scored}/{len(news)}</strong> articles scored by AI &nbsp;·&nbsp;
        📰 <strong style='color:white;'>{len(news)}</strong> relevant articles &nbsp;·&nbsp;
        🎯 <strong style='color:#00d4aa;'>Finance-filtered</strong>
    </div>""", unsafe_allow_html=True)

    # Sentiment counts
    sentiments = [n["sentiment"] for n in news]
    pos_count  = sentiments.count("Positive")
    neg_count  = sentiments.count("Negative")
    neu_count  = sentiments.count("Neutral")
    total      = len(sentiments) or 1
    bull_pct   = round(pos_count / total * 100)
    bear_pct   = round(neg_count / total * 100)

    if pos_count > neg_count:   overall, overall_color = "Bullish 🟢", "#00d4aa"
    elif neg_count > pos_count: overall, overall_color = "Bearish 🔴", "#ff4757"
    else:                       overall, overall_color = "Neutral 🟡", "#f0a500"

    nc1, nc2, nc3, nc4, nc5 = st.columns(5)
    with nc1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Overall Sentiment</div><div style='font-size:17px; font-weight:700; color:{overall_color};'>{overall}</div></div>", unsafe_allow_html=True)
    with nc2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>🟢 Positive</div><div class='metric-value' style='color:#00d4aa;'>{pos_count}</div><div style='color:#8892a4; font-size:11px;'>{bull_pct}% of articles</div></div>", unsafe_allow_html=True)
    with nc3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>🔴 Negative</div><div class='metric-value' style='color:#ff4757;'>{neg_count}</div><div style='color:#8892a4; font-size:11px;'>{bear_pct}% of articles</div></div>", unsafe_allow_html=True)
    with nc4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>🟡 Neutral</div><div class='metric-value' style='color:#f0a500;'>{neu_count}</div><div style='color:#8892a4; font-size:11px;'>{100-bull_pct-bear_pct}% of articles</div></div>", unsafe_allow_html=True)
    with nc5:
        score = round((pos_count - neg_count) / total * 100)
        sc    = "#00d4aa" if score > 0 else "#ff4757" if score < 0 else "#f0a500"
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Sentiment Score</div><div class='metric-value' style='color:{sc};'>{score:+d}</div><div style='color:#8892a4; font-size:11px;'>-100 (bearish) to +100 (bullish)</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts side by side
    chart_n1, chart_n2 = st.columns(2)
    with chart_n1:
        fig_sent = go.Figure(go.Bar(
            x=["Positive", "Neutral", "Negative"],
            y=[pos_count, neu_count, neg_count],
            marker_color=["#00d4aa", "#f0a500", "#ff4757"],
            text=[f"{v} articles" for v in [pos_count, neu_count, neg_count]],
            textposition="auto"
        ))
        fig_sent.update_layout(
            paper_bgcolor="#0a0e1a", plot_bgcolor="#0d1220",
            font=dict(color="white"), height=240,
            margin=dict(t=30, b=20), showlegend=False,
            title=dict(text="Sentiment Distribution", font=dict(color="white", size=13))
        )
        fig_sent.update_xaxes(gridcolor="#1a2035")
        fig_sent.update_yaxes(gridcolor="#1a2035")
        st.plotly_chart(fig_sent, use_container_width=True)

    with chart_n2:
        src_counts = {}
        for a in news:
            s = a.get("source","Unknown")
            src_counts[s] = src_counts.get(s,0) + 1
        fig_src = go.Figure(go.Bar(
            x=list(src_counts.keys()),
            y=list(src_counts.values()),
            marker_color="#1b4fd8",
            text=list(src_counts.values()),
            textposition="auto"
        ))
        fig_src.update_layout(
            paper_bgcolor="#0a0e1a", plot_bgcolor="#0d1220",
            font=dict(color="white"), height=240,
            margin=dict(t=30, b=20), showlegend=False,
            title=dict(text="Articles by Source", font=dict(color="white", size=13))
        )
        fig_src.update_xaxes(gridcolor="#1a2035", tickangle=-30)
        fig_src.update_yaxes(gridcolor="#1a2035")
        st.plotly_chart(fig_src, use_container_width=True)

    # Filter bar
    st.markdown("<div class='section-header'>📋 Articles</div>", unsafe_allow_html=True)
    filter_cols = st.columns(3)
    with filter_cols[0]:
        filter_sent = st.selectbox("Filter by Sentiment", ["All", "Positive", "Negative", "Neutral"], key="news_filter_sent")
    with filter_cols[1]:
        all_sources = ["All"] + list(set(a["source"] for a in news if a.get("source")))
        filter_src  = st.selectbox("Filter by Source", all_sources, key="news_filter_src")
    with filter_cols[2]:
        sort_order = st.selectbox("Sort by", ["Latest First", "Oldest First", "Most Positive First", "Most Negative First"], key="news_sort")

    # Apply filters
    filtered_news = [a for a in news
        if (filter_sent == "All" or a["sentiment"] == filter_sent)
        and (filter_src == "All" or a["source"] == filter_src)]

    # Apply sort
    if sort_order == "Oldest First":
        filtered_news = sorted(filtered_news, key=lambda x: x["published"])
    elif sort_order == "Most Positive First":
        order = {"Positive": 0, "Neutral": 1, "Negative": 2}
        filtered_news = sorted(filtered_news, key=lambda x: order.get(x["sentiment"], 1))
    elif sort_order == "Most Negative First":
        order = {"Negative": 0, "Neutral": 1, "Positive": 2}
        filtered_news = sorted(filtered_news, key=lambda x: order.get(x["sentiment"], 1))

    st.markdown(f"<small style='color:#8892a4;'>Showing {len(filtered_news)} of {len(news)} articles</small>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Article cards
    for article in filtered_news:
        s     = article["sentiment"]
        sc    = "sentiment-pos" if s == "Positive" else "sentiment-neg" if s == "Negative" else "sentiment-neu"
        bdr   = "#00d4aa" if s == "Positive" else "#ff4757" if s == "Negative" else "#f0a500"
        badge = "🟢" if s == "Positive" else "🔴" if s == "Negative" else "🟡"
        ai_badge = "<span style='background:#1b4fd820; border:1px solid #1b4fd840; border-radius:10px; padding:2px 7px; font-size:10px; color:#1b4fd8; margin-left:6px;'>🤖 AI</span>" if article.get("scored_by") == "AI" else ""
        url   = article.get("url","#")
        link  = f"<a href='{url}' target='_blank' style='color:#1b4fd8; font-size:11px; text-decoration:none;'>Read full article →</a>" if url != "#" else ""
        desc  = article.get("desc","")
        # Strip HTML tags from RSS descriptions before rendering
        import re as _re
        desc  = _re.sub(r'<[^>]+>', '', desc).strip()[:200]
        desc_html = f"<div style='color:#8892a4; font-size:12px; margin-top:6px; line-height:1.5;'>{desc}</div>" if desc else ""

        st.markdown(f"""
        <div style='background:#141928; border:1px solid #2a3350; border-left:3px solid {bdr};
             border-radius:10px; padding:16px; margin:8px 0;'>
            <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
                <div style='flex:1;'>
                    <div style='color:#e0e6f0; font-size:14px; font-weight:500; line-height:1.5;'>{article['title']}</div>
                    {desc_html}
                    <div style='margin-top:8px;'>
                        <span style='color:#8892a4; font-size:11px;'>{article['source']} · {article['published']}</span>
                        &nbsp;&nbsp;{link}
                    </div>
                </div>
                <div style='margin-left:16px; text-align:center; min-width:80px;'>
                    <div style='font-size:20px;'>{badge}</div>
                    <div class='{sc}' style='font-size:11px; font-weight:600;'>{s}</div>
                    {ai_badge}
                </div>
            </div>
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



# ── TAB 6: PRICE ALERTS ──
with tab6:
    st.markdown("<div class='section-header'>🔔 Price Alert Manager</div>", unsafe_allow_html=True)
    st.markdown("<small style='color:#8892a4;'>Set price alerts · Receive instant email notifications when triggered</small>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if "alerts" not in st.session_state:
        st.session_state.alerts = []

    # ── EMAIL SENDER CONFIG (loaded from Streamlit secrets only — never shown to users) ──
    try:
        st.session_state.alert_email_sender   = st.secrets.get("ALERT_SENDER_EMAIL", "")
        st.session_state.alert_email_password = st.secrets.get("ALERT_SENDER_PASSWORD", "")
    except:
        pass

    email_ready = bool(st.session_state.get("alert_email_sender"))
    if email_ready:
        st.markdown("""
        <div style='background:rgba(0,212,170,0.08); border:1px solid rgba(0,212,170,0.3);
             border-radius:8px; padding:10px 14px; margin-bottom:16px;'>
            <span style='color:#00d4aa; font-size:13px; font-weight:600;'>
                ✅ Email alerts active — you will receive notifications at your email address
            </span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:rgba(240,165,0,0.08); border:1px solid rgba(240,165,0,0.3);
             border-radius:8px; padding:10px 14px; margin-bottom:16px;'>
            <span style='color:#f0a500; font-size:13px; font-weight:600;'>
                ⚠️ Email alerts not configured — alerts will still trigger on screen but no emails will be sent.
            </span>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── ADD NEW ALERT ──
    st.markdown("<div class='section-header'>➕ Create New Alert</div>", unsafe_allow_html=True)
    na1, na2, na3, na4, na5 = st.columns(5)
    all_assets_for_alert = {**US_TICKERS, **CRYPTO_TICKERS, **COMMODITIES_TICKERS, **{n: s for n, s in NGX_SYMBOLS.items()}}

    with na1:
        alert_asset   = st.selectbox("Asset", list(all_assets_for_alert.keys()), key="alert_asset_sel")
    with na2:
        alert_dir     = st.selectbox("Condition", ["🔴 Price rises ABOVE", "🟢 Price falls BELOW"], key="alert_dir_sel")
    with na3:
        alert_asset_ticker = all_assets_for_alert[alert_asset]
        alert_live_price   = get_live_price(alert_asset_ticker).get("price", 0)
        st.markdown(f"<div style='padding:4px 0;'><span style='color:#8892a4; font-size:11px;'>LIVE PRICE</span><br><span style='color:#1b4fd8; font-size:16px; font-weight:700;'>${alert_live_price:,.2f}</span></div>", unsafe_allow_html=True)
        alert_level   = st.number_input("Target Price", min_value=0.0, value=float(round(alert_live_price * 1.05, 2)) if alert_live_price else 0.0, step=0.01, key="alert_level_inp")
    with na4:
        alert_to_email = st.text_input("Send alert to", placeholder="recipient@email.com", key="alert_to_email_inp")
    with na5:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔔 Create Alert", use_container_width=True, key="create_alert_btn"):
            if not alert_to_email:
                st.error("Enter recipient email")
            elif alert_level <= 0:
                st.error("Enter a valid price level")
            else:
                atype = "high" if "ABOVE" in alert_dir else "low"
                st.session_state.alerts.append({
                    "id":        len(st.session_state.alerts) + 1,
                    "name":      alert_asset,
                    "ticker":    alert_asset_ticker,
                    "type":      atype,
                    "level":     alert_level,
                    "email":     alert_to_email,
                    "active":    True,
                    "triggered": False,
                    "created":   datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
                st.success(f"✅ Alert created: {alert_asset} {'above' if atype=='high' else 'below'} ${alert_level:,.2f} → {alert_to_email}")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── MANUAL CHECK + ACTIVE ALERTS TABLE ──
    active_alerts  = [a for a in st.session_state.alerts if a.get("active")]
    fired_alerts   = [a for a in st.session_state.alerts if a.get("triggered")]

    col_check, col_clear = st.columns([1, 1])
    with col_check:
        if st.button("🔍 Check All Alerts Now", use_container_width=True, key="manual_check"):
            try:
                sender_e = st.secrets.get("ALERT_SENDER_EMAIL", "")
                sender_p = st.secrets.get("ALERT_SENDER_PASSWORD", "")
            except:
                sender_e = st.session_state.get("alert_email_sender", "")
                sender_p = st.session_state.get("alert_email_password", "")
            fired = check_and_fire_alerts(st.session_state.alerts, sender_e, sender_p)
            if fired:
                for alert, cp in fired:
                    arrow = "🔴" if alert["type"] == "high" else "🟢"
                    direct = "ABOVE" if alert["type"] == "high" else "BELOW"
                    st.success(f"{arrow} TRIGGERED: {alert['name']} is {direct} ${alert['level']:,.2f} — Current: ${cp:,.2f}")
                    if sender_e:
                        st.info(f"📧 Email sent to {alert['email']}")
                    else:
                        st.warning("⚠️ Email not sent — ALERT_SENDER_EMAIL not set in Streamlit Secrets")
                st.rerun()
            else:
                st.info(f"✅ Checked {len(active_alerts)} alert(s) — none triggered yet.")
    with col_clear:
        if st.button("🗑️ Clear All Alerts", use_container_width=True, key="clear_all_alerts"):
            st.session_state.alerts = []
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Active alerts table
    if active_alerts:
        st.markdown(f"<div class='section-header'>🟡 Active Alerts ({len(active_alerts)})</div>", unsafe_allow_html=True)
        for i, alert in enumerate(st.session_state.alerts):
            if not alert.get("active"): continue
            live_now  = get_live_price(alert["ticker"]).get("price", 0)
            arrow     = "🔴" if alert["type"] == "high" else "🟢"
            condition = "rises ABOVE" if alert["type"] == "high" else "falls BELOW"
            dist      = live_now - alert["level"] if alert["type"] == "high" else alert["level"] - live_now
            dist_pct  = (dist / alert["level"] * 100) if alert["level"] > 0 else 0
            dist_color = "#00d4aa" if dist < 0 else "#f0a500"
            ac1, ac2, ac3, ac4, ac5, ac6 = st.columns([2,1,1,1,2,1])
            with ac1: st.markdown(f"<div style='color:white; font-weight:600; font-size:14px;'>{alert['name']}</div><div style='color:#8892a4; font-size:11px;'>{alert['ticker']}</div>", unsafe_allow_html=True)
            with ac2: st.markdown(f"<div style='color:#8892a4; font-size:11px;'>CONDITION</div><div style='color:white; font-size:13px;'>{arrow} {condition}</div>", unsafe_allow_html=True)
            with ac3: st.markdown(f"<div style='color:#8892a4; font-size:11px;'>TARGET</div><div style='color:white; font-size:14px; font-weight:600;'>${alert['level']:,.2f}</div>", unsafe_allow_html=True)
            with ac4: st.markdown(f"<div style='color:#8892a4; font-size:11px;'>LIVE PRICE</div><div style='color:#1b4fd8; font-size:14px; font-weight:600;'>${live_now:,.2f}</div>", unsafe_allow_html=True)
            with ac5: st.markdown(f"<div style='color:#8892a4; font-size:11px;'>DISTANCE</div><div style='color:{dist_color}; font-size:13px; font-weight:600;'>${abs(dist):,.2f} ({abs(dist_pct):.1f}%) away</div><div style='color:#8892a4; font-size:11px;'>{alert['email']}</div>", unsafe_allow_html=True)
            with ac6:
                if st.button("❌", key=f"del_alert_{i}_{alert['id']}"):
                    st.session_state.alerts[i]["active"] = False
                    st.rerun()
            st.markdown("<hr style='border-color:#2a3350; margin:8px 0;'>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:#141928; border:1px solid #2a3350; border-radius:10px; padding:30px; text-align:center;'>
            <div style='font-size:28px;'>🔔</div>
            <div style='color:white; font-weight:600; margin:8px 0;'>No Active Alerts</div>
            <div style='color:#8892a4; font-size:13px;'>Create an alert above to get notified when prices move.</div>
        </div>""", unsafe_allow_html=True)

    # Triggered history
    if fired_alerts:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<div class='section-header'>✅ Triggered Alerts ({len(fired_alerts)})</div>", unsafe_allow_html=True)
        df_fired = pd.DataFrame([{
            "Asset": a["name"], "Ticker": a["ticker"],
            "Type": "🔴 Above" if a["type"]=="high" else "🟢 Below",
            "Target": f"${a['level']:,.2f}", "Email": a["email"],
            "Created": a.get("created",""),
        } for a in fired_alerts])
        st.dataframe(df_fired, use_container_width=True, hide_index=True)

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
