"""
NGX Real-Time Data Module — SOT Market Intelligence Dashboard
=============================================================
Primary:  iTick API (real-time NGX data)
Backup:   Web scraping (NGX official website)
Fallback: Last known prices (clearly labeled)
Author: Samuel Oyedokun
"""

import requests, os, time
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import streamlit as st

ITICK_BASE_URL = "https://api.itick.org"
try:
    ITICK_TOKEN = st.secrets.get("ITICK_API_TOKEN", "")
except:
    ITICK_TOKEN = os.getenv("ITICK_API_TOKEN", "")

ITICK_HEADERS = {"accept": "application/json", "token": ITICK_TOKEN}
WAT = timezone(timedelta(hours=1))

NGX_SYMBOLS = {
    "Dangote Cement": "DANGCEM", "GTBank (GTCO)": "GTCO",
    "Zenith Bank": "ZENITHBA", "MTN Nigeria": "MTNN",
    "Access Bank": "ACCESSCO", "Stanbic IBTC": "STANBIC",
    "FBN Holdings": "FBNH", "UBA": "UBA",
    "Nestle Nigeria": "NESTLE", "Airtel Africa": "AIRTELAFRI",
    "Seplat Energy": "SEPLAT", "BUA Cement": "BUACEMENT",
    "BUA Foods": "BUAFOODS", "Lafarge Africa": "WAPCO",
    "Okomu Oil": "OKOMUOIL", "Total Energies": "TOTAL",
    "Fidelity Bank": "FIDELITYBK", "Sterling Bank": "STERLINGBA",
    "Transcorp": "TRANSCORP", "Flour Mills": "FLOURMILL",
}

NGX_LAST_KNOWN = {
    "DANGCEM":   {"price": 810.00,"prev_close": 794.90,"high": 810.00,"low": 794.90,"volume": 1260225, "year_high": 950.00,"year_low": 420.00},
    "GTCO":      {"price": 58.50, "prev_close": 57.80, "high": 59.20, "low": 57.50, "volume": 8700000, "year_high": 68.00, "year_low": 32.00},
    "ZENITHBA":  {"price": 42.00, "prev_close": 42.35, "high": 42.80, "low": 41.60, "volume": 6100000, "year_high": 50.00, "year_low": 24.00},
    "MTNN":      {"price": 240.00,"prev_close": 238.00,"high": 242.00,"low": 237.00,"volume": 3200000, "year_high": 310.00,"year_low": 160.00},
    "ACCESSCO":  {"price": 22.50, "prev_close": 22.40, "high": 22.80, "low": 22.20, "volume": 10500000,"year_high": 28.00, "year_low": 14.00},
    "STANBIC":   {"price": 78.00, "prev_close": 77.20, "high": 78.50, "low": 77.00, "volume": 520000,  "year_high": 92.00, "year_low": 55.00},
    "FBNH":      {"price": 28.00, "prev_close": 28.20, "high": 28.50, "low": 27.80, "volume": 5100000, "year_high": 36.00, "year_low": 18.00},
    "UBA":       {"price": 26.50, "prev_close": 26.00, "high": 26.80, "low": 25.90, "volume": 7200000, "year_high": 32.00, "year_low": 16.00},
    "NESTLE":    {"price": 1200.0,"prev_close": 1190.0,"high": 1215.0,"low": 1185.0,"volume": 210000,  "year_high": 1500.0,"year_low": 800.00},
    "AIRTELAFRI":{"price": 2050.0,"prev_close": 2035.0,"high": 2070.0,"low": 2030.0,"volume": 320000,  "year_high": 2600.0,"year_low": 1400.0},
    "SEPLAT":    {"price": 4200.0,"prev_close": 4180.0,"high": 4250.0,"low": 4160.0,"volume": 180000,  "year_high": 5000.0,"year_low": 2800.0},
    "BUACEMENT": {"price": 115.00,"prev_close": 114.00,"high": 116.00,"low": 113.50,"volume": 950000,  "year_high": 140.00,"year_low": 75.00},
    "BUAFOODS":  {"price": 390.00,"prev_close": 388.00,"high": 395.00,"low": 386.00,"volume": 400000,  "year_high": 450.00,"year_low": 280.00},
    "WAPCO":     {"price": 42.00, "prev_close": 41.50, "high": 42.50, "low": 41.20, "volume": 750000,  "year_high": 55.00, "year_low": 28.00},
    "OKOMUOIL":  {"price": 380.00,"prev_close": 378.00,"high": 385.00,"low": 376.00,"volume": 120000,  "year_high": 480.00,"year_low": 260.00},
    "TOTAL":     {"price": 460.00,"prev_close": 458.00,"high": 465.00,"low": 455.00,"volume": 95000,   "year_high": 560.00,"year_low": 320.00},
    "FIDELITYBK":{"price": 12.50, "prev_close": 12.40, "high": 12.70, "low": 12.30, "volume": 12000000,"year_high": 16.00, "year_low": 7.50},
    "STERLINGBA":{"price": 5.80,  "prev_close": 5.75,  "high": 5.90,  "low": 5.70,  "volume": 8000000, "year_high": 7.50,  "year_low": 3.80},
    "TRANSCORP": {"price": 8.20,  "prev_close": 8.10,  "high": 8.35,  "low": 8.05,  "volume": 15000000,"year_high": 11.00, "year_low": 4.50},
    "FLOURMILL": {"price": 48.00, "prev_close": 47.50, "high": 48.50, "low": 47.20, "volume": 680000,  "year_high": 58.00, "year_low": 32.00},
}

def is_market_open():
    now = datetime.now(WAT)
    if now.weekday() >= 5: return False
    return now.replace(hour=10,minute=0,second=0) <= now <= now.replace(hour=14,minute=30,second=0)

def get_market_status():
    now = datetime.now(WAT)
    if now.weekday() >= 5: return "🔴 Weekend — Closed", "#ff4757"
    if is_market_open(): return "🟢 Market Open", "#00d4aa"
    if now.hour < 10: return "🟡 Pre-Market", "#f0a500"
    return "🔴 Market Closed", "#ff4757"

def _parse_quote(data, symbol):
    d = data.get("data", {})
    price = float(d.get("p", d.get("ld", 0)) or 0)
    prev  = float(d.get("pc", d.get("ld", price)) or price)
    ts    = d.get("t", 0)
    try:
        as_of = datetime.fromtimestamp(int(ts)/1000, tz=WAT).strftime("%Y-%m-%d %H:%M WAT")
    except:
        as_of = datetime.now(WAT).strftime("%Y-%m-%d %H:%M WAT")
    lk = NGX_LAST_KNOWN.get(symbol.upper(), {})
    return {
        "symbol": symbol.upper(), "price": price, "prev_close": prev,
        "change": float(d.get("ch", round(price-prev,4)) or 0),
        "change_pct": float(d.get("chp", 0) or 0),
        "high": float(d.get("h", price) or price),
        "low":  float(d.get("l", price) or price),
        "volume": float(d.get("v", 0) or 0),
        "year_high": lk.get("year_high", 0),
        "year_low":  lk.get("year_low",  0),
        "as_of": as_of, "source": "iTick API (Live)",
    }

def fetch_itick_single(symbol):
    if not ITICK_TOKEN: return None
    try:
        r = requests.get(f"{ITICK_BASE_URL}/stock/quote", headers=ITICK_HEADERS,
                         params={"region":"NG","code":symbol.upper()}, timeout=10)
        data = r.json()
        if data.get("code") == 0 and data.get("data"):
            return _parse_quote(data, symbol)
    except Exception as e:
        print(f"iTick error {symbol}: {e}")
    return None

def fetch_itick_all():
    if not ITICK_TOKEN: return {}
    symbols = list(NGX_SYMBOLS.values())
    results = {}
    for i, symbol in enumerate(symbols):
        q = fetch_itick_single(symbol)
        if q:
            results[symbol.upper()] = q
        # Rate limit: 5 calls/min = 1 call per 12s
        if (i + 1) % 5 == 0 and i + 1 < len(symbols):
            time.sleep(12)
    return results

def scrape_ngx_backup():
    hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    for url in ["https://ngxgroup.com/exchange/trade-data/equities-price-list/",
                "https://stockswatch.com.ng/market-data/stock-prices/"]:
        try:
            r = requests.get(url, headers=hdrs, timeout=15)
            if r.status_code != 200: continue
            tables = pd.read_html(r.text)
            if not tables: continue
            df = tables[0]
            df.columns = [str(c).upper().strip() for c in df.columns]
            results = {}
            for _, row in df.iterrows():
                sym = str(row.get("SYMBOL", row.get("TICKER",""))).strip().upper()
                if not sym or sym == "NAN": continue
                try:
                    close = float(str(row.get("CLOSE", row.get("LAST",0))).replace(",","").replace("₦",""))
                    prev  = float(str(row.get("PREV CLOSE", close)).replace(",","").replace("₦",""))
                    lk    = NGX_LAST_KNOWN.get(sym, {})
                    results[sym] = {
                        "symbol": sym, "price": close, "prev_close": prev,
                        "change": round(close-prev, 4),
                        "change_pct": round(((close-prev)/prev)*100, 2) if prev else 0,
                        "high": float(str(row.get("HIGH",close)).replace(",","").replace("₦","")),
                        "low":  float(str(row.get("LOW", close)).replace(",","").replace("₦","")),
                        "volume": float(str(row.get("VOLUME",0)).replace(",","")),
                        "year_high": lk.get("year_high",0), "year_low": lk.get("year_low",0),
                        "as_of": datetime.now(WAT).strftime("%Y-%m-%d %H:%M WAT"),
                        "source": f"Web Scrape ({url.split('/')[2]})",
                    }
                except: continue
            if len(results) > 5: return results
        except: continue
    return {}

def get_last_known_prices():
    result = {}
    for sym, d in NGX_LAST_KNOWN.items():
        result[sym] = {
            "symbol": sym, "price": d["price"], "prev_close": d["prev_close"],
            "change": round(d["price"]-d["prev_close"],4),
            "change_pct": round(((d["price"]-d["prev_close"])/d["prev_close"])*100,2),
            "high": d["high"], "low": d["low"], "volume": d["volume"],
            "year_high": d["year_high"], "year_low": d["year_low"],
            "as_of": "March 2026 — Live data unavailable",
            "source": "Last Known (Offline)",
        }
    return result

@st.cache_data(ttl=300)
def fetch_ngx_prices():
    """Main function: tries iTick → scraping → last known"""
    if ITICK_TOKEN:
        prices = fetch_itick_all()
        if prices and len(prices) >= 5:
            return prices, "iTick API (Live)", datetime.now(WAT).strftime("%Y-%m-%d %H:%M WAT")
    prices = scrape_ngx_backup()
    if prices and len(prices) >= 5:
        return prices, "Web Scrape (End of Day)", datetime.now(WAT).strftime("%Y-%m-%d %H:%M WAT")
    return get_last_known_prices(), "Last Known (Offline)", "March 2026"

def get_ngx_stock(symbol, all_prices):
    symbol = symbol.upper()
    d = all_prices.get(symbol) or {}
    if not d and symbol in NGX_LAST_KNOWN:
        lk = NGX_LAST_KNOWN[symbol]
        d = {**lk, "change": round(lk["price"]-lk["prev_close"],4),
             "change_pct": round(((lk["price"]-lk["prev_close"])/lk["prev_close"])*100,2),
             "source": "Last Known (Offline)", "as_of": "March 2026"}
    return {
        "price":      d.get("price", 0),
        "change":     d.get("change", 0),
        "change_pct": d.get("change_pct", 0),
        "high":       d.get("year_high", d.get("high", 0)),
        "low":        d.get("year_low",  d.get("low",  0)),
        "volume":     d.get("volume", 0),
        "source":     d.get("source", "N/A"),
        "as_of":      d.get("as_of", "N/A"),
    }

def get_ngx_history(symbol, all_prices, period="3mo"):
    """Fetch K-line history from iTick, fall back to simulation"""
    symbol = symbol.upper()
    if ITICK_TOKEN:
        try:
            period_map = {"1mo":("D",22),"3mo":("D",66),"6mo":("D",130),
                          "1y":("D",252),"2y":("W",104),"5y":("M",60)}
            ktype, limit = period_map.get(period, ("D",66))
            r = requests.get(f"{ITICK_BASE_URL}/stock/kline", headers=ITICK_HEADERS,
                params={"region":"NG","code":symbol,"kType":ktype,"limit":limit}, timeout=15)
            data = r.json()
            if data.get("code") == 0 and data.get("data"):
                rows = data["data"]
                df = pd.DataFrame(rows)
                df = df.rename(columns={"t":"ts","o":"Open","h":"High","l":"Low","c":"Close","v":"Volume"})
                df["Date"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_convert(WAT)
                df = df.set_index("Date")[["Open","High","Low","Close","Volume"]].astype(float)
                if not df.empty and len(df) > 5:
                    return df
        except Exception as e:
            print(f"kline error {symbol}: {e}")

    # Simulation anchored to live price
    base = get_ngx_stock(symbol, all_prices).get("price", 100) or 100
    days = {"1mo":22,"3mo":66,"6mo":130,"1y":252,"2y":504,"5y":1260}.get(period,66)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="B")
    np.random.seed(abs(hash(symbol)) % 9999)
    ret = np.random.normal(0.0002, 0.010, days)
    px  = base * np.exp(np.cumsum(ret) - np.cumsum(ret)[-1])
    return pd.DataFrame({
        "Open":   px*(1-np.random.uniform(0,0.004,days)),
        "High":   px*(1+np.random.uniform(0.001,0.012,days)),
        "Low":    px*(1-np.random.uniform(0.001,0.012,days)),
        "Close":  px,
        "Volume": np.random.randint(200000,3000000,days).astype(float),
    }, index=dates)
