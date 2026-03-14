"""
NGX Real Data Module — SOT Market Intelligence Dashboard
=========================================================
Fetches real end-of-day NGX stock prices from multiple sources:
  1. NGX Group official website (primary)
  2. Stockswatch.com.ng (backup)
  3. Cached fallback (last known prices) if all sources fail

NGX market hours: 10:00 AM – 2:30 PM WAT (Monday–Friday)
Prices update after market close (~3:00 PM WAT daily)

Author: Samuel Oyedokun
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import streamlit as st

# ── HEADERS ──
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

CACHE_FILE = "/tmp/ngx_cache.json"
CACHE_TTL_HOURS = 6  # Refresh every 6 hours

# ── STOCK SYMBOLS MAPPING ──
# Maps display names to NGX ticker symbols
NGX_SYMBOLS = {
    "Dangote Cement":   "DANGCEM",
    "GTBank (GTCO)":    "GTCO",
    "Zenith Bank":      "ZENITHBA",
    "MTN Nigeria":      "MTNN",
    "Access Bank":      "ACCESSCO",
    "Stanbic IBTC":     "STANBIC",
    "FBN Holdings":     "FBNH",
    "UBA":              "UBA",
    "Nestle Nigeria":   "NESTLE",
    "Airtel Africa":    "AIRTELAFRI",
    "Seplat Energy":    "SEPLAT",
    "BUA Cement":       "BUACEMENT",
    "BUA Foods":        "BUAFOODS",
    "Lafarge Africa":   "WAPCO",
    "Okomu Oil":        "OKOMUOIL",
    "Total Energies":   "TOTAL",
    "Fidelity Bank":    "FIDELITYBK",
    "Sterling Bank":    "STERLINGBA",
    "Transcorp":        "TRANSCORP",
    "Flour Mills":      "FLOURMILL",
}

# ── LAST KNOWN PRICES (updated March 2026) ──
# Used as final fallback — clearly labeled as such in UI
NGX_LAST_KNOWN = {
    "DANGCEM":   {"price": 650.00,  "prev_close": 645.00,  "high": 655.00,  "low": 642.00,  "volume": 1_250_000,  "year_high": 920.00,  "year_low": 410.00},
    "GTCO":      {"price": 58.50,   "prev_close": 57.80,   "high": 59.20,   "low": 57.50,   "volume": 8_700_000,  "year_high": 68.00,   "year_low": 32.00},
    "ZENITHBA":  {"price": 42.00,   "prev_close": 42.35,   "high": 42.80,   "low": 41.60,   "volume": 6_100_000,  "year_high": 50.00,   "year_low": 24.00},
    "MTNN":      {"price": 240.00,  "prev_close": 238.00,  "high": 242.00,  "low": 237.00,  "volume": 3_200_000,  "year_high": 310.00,  "year_low": 160.00},
    "ACCESSCO":  {"price": 22.50,   "prev_close": 22.40,   "high": 22.80,   "low": 22.20,   "volume": 10_500_000, "year_high": 28.00,   "year_low": 14.00},
    "STANBIC":   {"price": 78.00,   "prev_close": 77.20,   "high": 78.50,   "low": 77.00,   "volume": 520_000,    "year_high": 92.00,   "year_low": 55.00},
    "FBNH":      {"price": 28.00,   "prev_close": 28.20,   "high": 28.50,   "low": 27.80,   "volume": 5_100_000,  "year_high": 36.00,   "year_low": 16.00},
    "UBA":       {"price": 26.50,   "prev_close": 26.00,   "high": 26.80,   "low": 25.90,   "volume": 7_200_000,  "year_high": 32.00,   "year_low": 16.00},
    "NESTLE":    {"price": 1200.00, "prev_close": 1190.00, "high": 1215.00, "low": 1185.00, "volume": 210_000,    "year_high": 1500.00, "year_low": 800.00},
    "AIRTELAFRI":{"price": 2050.00, "prev_close": 2035.00, "high": 2070.00, "low": 2030.00, "volume": 320_000,    "year_high": 2600.00, "year_low": 1400.00},
    "SEPLAT":    {"price": 4200.00, "prev_close": 4180.00, "high": 4250.00, "low": 4160.00, "volume": 180_000,    "year_high": 5000.00, "year_low": 2800.00},
    "BUACEMENT": {"price": 115.00,  "prev_close": 114.00,  "high": 116.00,  "low": 113.50,  "volume": 950_000,    "year_high": 140.00,  "year_low": 75.00},
    "BUAFOODS":  {"price": 390.00,  "prev_close": 388.00,  "high": 395.00,  "low": 386.00,  "volume": 400_000,    "year_high": 450.00,  "year_low": 280.00},
    "WAPCO":     {"price": 42.00,   "prev_close": 41.50,   "high": 42.50,   "low": 41.20,   "volume": 750_000,    "year_high": 55.00,   "year_low": 28.00},
    "OKOMUOIL":  {"price": 380.00,  "prev_close": 378.00,  "high": 385.00,  "low": 376.00,  "volume": 120_000,    "year_high": 480.00,  "year_low": 260.00},
    "TOTAL":     {"price": 460.00,  "prev_close": 458.00,  "high": 465.00,  "low": 455.00,  "volume": 95_000,     "year_high": 560.00,  "year_low": 320.00},
    "FIDELITYBK":{"price": 12.50,  "prev_close": 12.40,   "high": 12.70,   "low": 12.30,   "volume": 12_000_000, "year_high": 16.00,   "year_low": 7.50},
    "STERLINGBA":{"price": 5.80,   "prev_close": 5.75,    "high": 5.90,    "low": 5.70,    "volume": 8_000_000,  "year_high": 7.50,    "year_low": 3.80},
    "TRANSCORP": {"price": 8.20,   "prev_close": 8.10,    "high": 8.35,    "low": 8.05,    "volume": 15_000_000, "year_high": 11.00,   "year_low": 4.50},
    "FLOURMILL": {"price": 48.00,  "prev_close": 47.50,   "high": 48.50,   "low": 47.20,   "volume": 680_000,    "year_high": 58.00,   "year_low": 32.00},
}


# ── CACHE HELPERS ──
def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
            cached_time = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600
            if age_hours < CACHE_TTL_HOURS:
                return data.get("prices", {}), data.get("timestamp"), True
            return data.get("prices", {}), data.get("timestamp"), False
    except:
        pass
    return {}, None, False


def save_cache(prices):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "prices": prices}, f)
    except:
        pass


# ── SOURCE 1: NGX GROUP OFFICIAL ──
def scrape_ngx_official():
    """Scrape NGX Group official price list page"""
    url = "https://ngxgroup.com/exchange/trade-data/equities-price-list/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.content, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            return {}
        df = pd.read_html(str(tables[0]))[0]
        df.columns = [str(c).strip().upper() for c in df.columns]

        prices = {}
        for _, row in df.iterrows():
            symbol = str(row.get("SYMBOL", row.get("TICKER", ""))).strip().upper()
            if not symbol or symbol == "NAN":
                continue
            try:
                close = float(str(row.get("CLOSE", row.get("CLOSING PRICE", 0))).replace(",", ""))
                prev  = float(str(row.get("PREV CLOSE", row.get("OPENING PRICE", close))).replace(",", ""))
                high  = float(str(row.get("HIGH", close)).replace(",", ""))
                low   = float(str(row.get("LOW", close)).replace(",", ""))
                vol   = float(str(row.get("VOLUME", row.get("DEALS", 0))).replace(",", ""))
                change = round(close - prev, 4)
                change_pct = round((change / prev) * 100, 2) if prev else 0
                prices[symbol] = {
                    "price": close, "prev_close": prev,
                    "change": change, "change_pct": change_pct,
                    "high": high, "low": low, "volume": vol,
                    "source": "NGX Official",
                    "as_of": datetime.now().strftime("%Y-%m-%d %H:%M WAT")
                }
            except:
                continue
        return prices
    except:
        return {}


# ── SOURCE 2: STOCKSWATCH ──
def scrape_stockswatch():
    """Scrape stockswatch.com.ng as backup"""
    url = "https://stockswatch.com.ng/market-data/stock-prices/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.content, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            return {}
        df = pd.read_html(str(tables[0]))[0]
        df.columns = [str(c).strip().upper() for c in df.columns]

        prices = {}
        for _, row in df.iterrows():
            symbol = str(row.get("SYMBOL", row.get("CODE", ""))).strip().upper()
            if not symbol or symbol == "NAN":
                continue
            try:
                close = float(str(row.get("LAST", row.get("PRICE", row.get("CLOSE", 0)))).replace(",", "").replace("₦", ""))
                prev  = float(str(row.get("PREV", row.get("PREV CLOSE", close))).replace(",", "").replace("₦", ""))
                change = round(close - prev, 4)
                change_pct = round((change / prev) * 100, 2) if prev else 0
                prices[symbol] = {
                    "price": close, "prev_close": prev,
                    "change": change, "change_pct": change_pct,
                    "high": float(str(row.get("HIGH", close)).replace(",", "").replace("₦", "")),
                    "low":  float(str(row.get("LOW", close)).replace(",", "").replace("₦", "")),
                    "volume": float(str(row.get("VOLUME", row.get("VOL", 0))).replace(",", "")),
                    "source": "Stockswatch",
                    "as_of": datetime.now().strftime("%Y-%m-%d %H:%M WAT")
                }
            except:
                continue
        return prices
    except:
        return {}


# ── SOURCE 3: INVESTDATA ──
def scrape_investdata():
    """Scrape investdata.com.ng as second backup"""
    url = "https://investdata.com.ng/market-data/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.content, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            return {}
        df = pd.read_html(str(tables[0]))[0]
        df.columns = [str(c).strip().upper() for c in df.columns]
        prices = {}
        for _, row in df.iterrows():
            symbol = str(row.get("SYMBOL", row.get("TICKER", ""))).strip().upper()
            if not symbol or symbol == "NAN":
                continue
            try:
                close = float(str(row.get("CLOSE", row.get("PRICE", 0))).replace(",", "").replace("₦", ""))
                prev  = float(str(row.get("PREV", close)).replace(",", "").replace("₦", ""))
                change = round(close - prev, 4)
                change_pct = round((change / prev) * 100, 2) if prev else 0
                prices[symbol] = {
                    "price": close, "prev_close": prev,
                    "change": change, "change_pct": change_pct,
                    "high": close, "low": close, "volume": 0,
                    "source": "Investdata",
                    "as_of": datetime.now().strftime("%Y-%m-%d %H:%M WAT")
                }
            except:
                continue
        return prices
    except:
        return {}


# ── MAIN FETCH FUNCTION ──
@st.cache_data(ttl=21600)  # Cache 6 hours
def fetch_ngx_prices():
    """
    Fetch NGX prices with multi-source fallback:
    1. Check cache (valid if < 6 hours old)
    2. Try NGX official website
    3. Try Stockswatch backup
    4. Try Investdata backup
    5. Use last known prices (clearly labeled)
    Returns: (prices_dict, source_label, as_of_timestamp)
    """
    # Check cache first
    cached, cached_time, is_fresh = load_cache()
    if is_fresh and cached:
        return cached, "Cached", cached_time

    # Try sources in order
    for scrape_fn, label in [
        (scrape_ngx_official, "NGX Official"),
        (scrape_stockswatch,  "Stockswatch"),
        (scrape_investdata,   "Investdata"),
    ]:
        prices = scrape_fn()
        if prices and len(prices) > 5:
            save_cache(prices)
            return prices, label, datetime.now().strftime("%Y-%m-%d %H:%M WAT")

    # Use stale cache if available
    if cached:
        return cached, "Stale Cache", cached_time

    # Final fallback — last known prices
    fallback = {}
    for symbol, data in NGX_LAST_KNOWN.items():
        fallback[symbol] = {
            **data,
            "change": round(data["price"] - data["prev_close"], 4),
            "change_pct": round(((data["price"] - data["prev_close"]) / data["prev_close"]) * 100, 2),
            "source": "Last Known (Offline)",
            "as_of": "March 2026 — Live data unavailable"
        }
    return fallback, "Last Known (Offline)", "March 2026"


def get_ngx_stock(symbol: str, all_prices: dict) -> dict:
    """Get price data for a single NGX symbol"""
    symbol = symbol.upper()
    if symbol in all_prices:
        d = all_prices[symbol]
        return {
            "price":      d.get("price", 0),
            "change":     d.get("change", 0),
            "change_pct": d.get("change_pct", 0),
            "high":       d.get("high", d.get("year_high", 0)),
            "low":        d.get("low", d.get("year_low", 0)),
            "volume":     d.get("volume", 0),
            "source":     d.get("source", "Unknown"),
            "as_of":      d.get("as_of", "Unknown"),
        }
    # Return last known if symbol not in scraped data
    if symbol in NGX_LAST_KNOWN:
        d = NGX_LAST_KNOWN[symbol]
        return {
            "price":      d["price"],
            "change":     round(d["price"] - d["prev_close"], 4),
            "change_pct": round(((d["price"] - d["prev_close"]) / d["prev_close"]) * 100, 2),
            "high":       d["year_high"],
            "low":        d["year_low"],
            "volume":     d["volume"],
            "source":     "Last Known (Offline)",
            "as_of":      "March 2026",
        }
    return {"price": 0, "change": 0, "change_pct": 0, "high": 0, "low": 0, "volume": 0, "source": "N/A", "as_of": "N/A"}


def is_market_open() -> bool:
    """Check if NGX market is currently open (10am-2:30pm WAT, Mon-Fri)"""
    from datetime import timezone, timedelta
    WAT = timezone(timedelta(hours=1))
    now = datetime.now(WAT)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open  = now.replace(hour=10, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=14, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def get_market_status() -> tuple:
    """Returns (status_text, status_color)"""
    if is_market_open():
        return "🟢 Market Open", "#00d4aa"
    from datetime import timezone, timedelta
    WAT = timezone(timedelta(hours=1))
    now = datetime.now(WAT)
    if now.weekday() >= 5:
        return "🔴 Weekend — Closed", "#ff4757"
    if now.hour < 10:
        return "🟡 Pre-Market", "#f0a500"
    return "🔴 Market Closed", "#ff4757"
