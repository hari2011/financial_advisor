"""Live market data from free APIs — zero cost, no API keys.

Data Sources:
  • yfinance     — Indices (Nifty, Sensex), Gold, Silver, Crude, Forex, Stocks
  • mfapi.in     — Mutual fund NAVs (direct API, no scraping)
  • NSE India    — Broad market indices with % change (session-based)

All data is cached with appropriate TTLs to avoid rate-limiting:
  • Indices/commodities: 5 min cache (prices move slowly enough)
  • Stock quotes:        2 min cache
  • Mutual fund NAVs:    30 min cache (NAVs update once daily)
  • FD/RBI rates:        6 hour cache (changes rarely)
"""

import time
import logging
import threading
from typing import Any

import requests
import yfinance as yf

logger = logging.getLogger("financegpt.tools.market")

# ──────────────────────── Cache ────────────────────────

_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.Lock()


def _get_cached(key: str, ttl: int) -> Any | None:
    with _cache_lock:
        if key in _cache:
            ts, val = _cache[key]
            if time.time() - ts < ttl:
                return val
    return None


def _set_cached(key: str, val: Any):
    with _cache_lock:
        _cache[key] = (time.time(), val)


# ──────────────────────── Constants ────────────────────────

# yfinance tickers for key Indian market data
_INDEX_TICKERS = {
    "nifty_50": {"symbol": "^NSEI", "name": "Nifty 50", "currency": "INR"},
    "sensex": {"symbol": "^BSESN", "name": "BSE Sensex", "currency": "INR"},
    "nifty_bank": {"symbol": "^NSEBANK", "name": "Nifty Bank", "currency": "INR"},
    "nifty_it": {"symbol": "^CNXIT", "name": "Nifty IT", "currency": "INR"},
}

_COMMODITY_TICKERS = {
    "gold_usd": {"symbol": "GC=F", "name": "Gold", "unit": "USD/oz"},
    "gold_inr": {"symbol": "GOLDBEES.NS", "name": "Gold ETF (India)", "unit": "₹/unit"},
    "silver_usd": {"symbol": "SI=F", "name": "Silver", "unit": "USD/oz"},
    "crude_oil": {"symbol": "CL=F", "name": "Crude Oil (WTI)", "unit": "USD/bbl"},
    "natural_gas": {"symbol": "NG=F", "name": "Natural Gas", "unit": "USD/MMBtu"},
}

_FOREX_TICKERS = {
    "usd_inr": {"symbol": "INR=X", "name": "USD/INR", "unit": "₹"},
    "eur_inr": {"symbol": "EURINR=X", "name": "EUR/INR", "unit": "₹"},
    "gbp_inr": {"symbol": "GBPINR=X", "name": "GBP/INR", "unit": "₹"},
}

# Popular NSE stocks (symbol → display name)
_POPULAR_STOCKS = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "ITC": "ITC",
    "BHARTIARTL": "Bharti Airtel",
    "SBIN": "State Bank of India",
    "ICICIBANK": "ICICI Bank",
    "HINDUNILVR": "Hindustan Unilever",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro",
    "WIPRO": "Wipro",
    "AXISBANK": "Axis Bank",
    "TATAMOTORS": "Tata Motors",
    "TATASTEEL": "Tata Steel",
    "MARUTI": "Maruti Suzuki",
    "BAJFINANCE": "Bajaj Finance",
    "ADANIENT": "Adani Enterprises",
    "HCLTECH": "HCL Technologies",
    "SUNPHARMA": "Sun Pharmaceutical",
}

# Popular mutual fund scheme codes (MFAPI)
_POPULAR_MF = {
    "119551": "Nippon India Large Cap Fund",
    "120503": "ICICI Prudential Bluechip Fund",
    "100356": "SBI Blue Chip Fund",
    "118989": "Mirae Asset Large Cap Fund",
    "119597": "Axis Bluechip Fund",
    "120505": "ICICI Prudential Value Discovery Fund",
    "100526": "SBI Small Cap Fund",
    "125497": "Parag Parikh Flexi Cap Fund",
    "118834": "Kotak Emerging Equity Fund",
    "120847": "Nippon India Small Cap Fund",
}

# Current Indian FD/RBI rates (manually maintained, updated infrequently)
_FD_RATES = {
    "rbi_repo_rate": 6.00,
    "sbi_fd_1yr": 6.80,
    "sbi_fd_3yr": 7.00,
    "sbi_fd_5yr": 6.50,
    "post_office_savings": 4.00,
    "ppf_rate": 7.10,
    "sukanya_samriddhi": 8.20,
    "nsc_rate": 7.70,
    "epf_rate": 8.25,
    "senior_citizen_savings": 8.20,
}


# ──────────────────────── yfinance Helpers ────────────────────────

def _yf_quote(symbol: str) -> dict | None:
    """Fetch a single quote from yfinance. Returns dict with price data or None."""
    try:
        tk = yf.Ticker(symbol)
        fi = tk.fast_info
        price = fi.last_price
        if price is None:
            return None

        result = {
            "price": round(price, 2),
            "prev_close": round(fi.regular_market_previous_close or 0, 2),
        }

        # Calculate change
        if result["prev_close"] and result["prev_close"] > 0:
            change = result["price"] - result["prev_close"]
            result["change"] = round(change, 2)
            result["change_pct"] = round((change / result["prev_close"]) * 100, 2)
        else:
            result["change"] = 0
            result["change_pct"] = 0

        # Day range (may be None after hours)
        result["day_low"] = round(fi.day_low, 2) if fi.day_low else None
        result["day_high"] = round(fi.day_high, 2) if fi.day_high else None
        result["volume"] = fi.last_volume

        # 52-week range
        result["year_low"] = round(fi.year_low, 2) if fi.year_low else None
        result["year_high"] = round(fi.year_high, 2) if fi.year_high else None

        return result
    except Exception as e:
        logger.warning(f"yfinance quote failed for {symbol}: {e}")
        return None


# ──────────────────────── Public API ────────────────────────

def get_indices() -> dict:
    """Get live Indian market indices (Nifty 50, Sensex, Bank Nifty, Nifty IT).

    Returns: {"nifty_50": {"name": ..., "price": ..., "change_pct": ...}, ...}
    Cached for 5 minutes.
    """
    cached = _get_cached("indices", 300)
    if cached:
        return cached

    result = {}
    for key, spec in _INDEX_TICKERS.items():
        quote = _yf_quote(spec["symbol"])
        if quote:
            result[key] = {
                "name": spec["name"],
                **quote,
            }

    if result:
        _set_cached("indices", result)
    return result


def get_commodities() -> dict:
    """Get live commodity prices (Gold, Silver, Crude Oil).

    Returns prices in USD. Use get_forex() for INR conversion.
    Cached for 5 minutes.
    """
    cached = _get_cached("commodities", 300)
    if cached:
        return cached

    result = {}
    for key, spec in _COMMODITY_TICKERS.items():
        quote = _yf_quote(spec["symbol"])
        if quote:
            result[key] = {
                "name": spec["name"],
                "unit": spec["unit"],
                **quote,
            }

    if result:
        _set_cached("commodities", result)
    return result


def get_forex() -> dict:
    """Get live forex rates (USD/INR, EUR/INR, GBP/INR).

    Cached for 5 minutes.
    """
    cached = _get_cached("forex", 300)
    if cached:
        return cached

    result = {}
    for key, spec in _FOREX_TICKERS.items():
        quote = _yf_quote(spec["symbol"])
        if quote:
            result[key] = {
                "name": spec["name"],
                "unit": spec["unit"],
                **quote,
            }

    if result:
        _set_cached("forex", result)
    return result


def get_gold_price_inr() -> dict | None:
    """Get gold price in INR per gram (converted from USD/oz via live forex).

    1 troy oz = 31.1035 grams.
    Cached for 5 minutes.
    """
    cached = _get_cached("gold_inr_gram", 300)
    if cached:
        return cached

    commodities = get_commodities()
    forex = get_forex()

    gold = commodities.get("gold_usd")
    usd_inr = forex.get("usd_inr")

    if not gold or not usd_inr:
        return None

    gold_usd_per_gram = gold["price"] / 31.1035
    inr_rate = usd_inr["price"]
    # 24K = 99.9% pure (commodity exchange price)
    gold_24k_per_gram = round(gold_usd_per_gram * inr_rate, 2)
    gold_24k_per_10g = round(gold_24k_per_gram * 10, 2)
    # 22K = 91.67% pure (standard jewelry gold in India)
    gold_22k_per_gram = round(gold_24k_per_gram * 22 / 24, 2)
    gold_22k_per_10g = round(gold_22k_per_gram * 10, 2)
    # 18K = 75% pure (premium jewelry)
    gold_18k_per_gram = round(gold_24k_per_gram * 18 / 24, 2)
    gold_18k_per_10g = round(gold_18k_per_gram * 10, 2)

    result = {
        "price_per_gram": gold_24k_per_gram,
        "price_per_10g": gold_24k_per_10g,
        "price_per_gram_24k": gold_24k_per_gram,
        "price_per_10g_24k": gold_24k_per_10g,
        "price_per_gram_22k": gold_22k_per_gram,
        "price_per_10g_22k": gold_22k_per_10g,
        "price_per_gram_18k": gold_18k_per_gram,
        "price_per_10g_18k": gold_18k_per_10g,
        "price_per_oz_usd": gold["price"],
        "usd_inr_rate": inr_rate,
        "change_pct": gold["change_pct"],
    }

    _set_cached("gold_inr_gram", result)
    return result


def get_stock_quote(symbol: str) -> dict | None:
    """Get live quote for an NSE/BSE stock.

    Args:
        symbol: NSE symbol (e.g., 'RELIANCE', 'TCS', 'INFY')
                Or full Yahoo symbol (e.g., 'RELIANCE.NS')

    Returns: {"name": ..., "price": ..., "change_pct": ..., ...} or None
    Cached for 2 minutes per stock.
    """
    # Normalize symbol
    symbol_clean = symbol.upper().strip()
    if not symbol_clean.endswith(".NS") and not symbol_clean.endswith(".BO"):
        yahoo_symbol = f"{symbol_clean}.NS"
    else:
        yahoo_symbol = symbol_clean
        symbol_clean = symbol_clean.replace(".NS", "").replace(".BO", "")

    cache_key = f"stock:{symbol_clean}"
    cached = _get_cached(cache_key, 120)
    if cached:
        return cached

    quote = _yf_quote(yahoo_symbol)
    if not quote:
        # Try BSE
        yahoo_bse = f"{symbol_clean}.BO"
        quote = _yf_quote(yahoo_bse)

    if quote:
        name = _POPULAR_STOCKS.get(symbol_clean, symbol_clean)
        result = {"name": name, "symbol": symbol_clean, **quote}
        _set_cached(cache_key, result)
        return result
    return None


def get_mutual_fund_nav(scheme_code: str) -> dict | None:
    """Get latest NAV for a mutual fund scheme via MFAPI.in (free, no key).

    Args:
        scheme_code: AMFI scheme code (e.g., '119551' for Nippon India Large Cap)

    Returns: {"name": ..., "nav": ..., "date": ...} or None
    Cached for 30 minutes (NAVs update once daily after market close).
    """
    cache_key = f"mf:{scheme_code}"
    cached = _get_cached(cache_key, 1800)
    if cached:
        return cached

    try:
        r = requests.get(
            f"https://api.mfapi.in/mf/{scheme_code}/latest",
            timeout=8,
            headers={"User-Agent": "FinanceGPT/1.0"},
        )
        if r.status_code != 200:
            return None

        data = r.json()
        meta = data.get("meta", {})
        nav_data = data.get("data", [{}])[0]

        result = {
            "name": meta.get("scheme_name", _POPULAR_MF.get(scheme_code, f"Scheme {scheme_code}")),
            "nav": float(nav_data.get("nav", 0)),
            "date": nav_data.get("date", ""),
            "category": meta.get("scheme_category", ""),
            "fund_house": meta.get("fund_house", ""),
            "scheme_code": scheme_code,
        }

        _set_cached(cache_key, result)
        return result
    except Exception as e:
        logger.warning(f"MFAPI lookup failed for {scheme_code}: {e}")
        return None


def search_mutual_fund(query: str) -> list[dict]:
    """Search mutual funds by name via MFAPI.in.

    Args:
        query: Search string (e.g., 'hdfc flexi cap', 'sbi small cap')

    Returns: List of {"schemeCode": ..., "schemeName": ...}
    Cached for 6 hours (fund list rarely changes).
    """
    cache_key = f"mf_search:{query.lower().strip()}"
    cached = _get_cached(cache_key, 21600)
    if cached:
        return cached

    try:
        r = requests.get(
            f"https://api.mfapi.in/mf/search?q={requests.utils.quote(query)}",
            timeout=8,
            headers={"User-Agent": "FinanceGPT/1.0"},
        )
        if r.status_code != 200:
            return []

        results = r.json()
        # Filter to direct/growth plans (most common for investors)
        filtered = [
            r for r in results
            if "direct" in r.get("schemeName", "").lower()
            and "growth" in r.get("schemeName", "").lower()
        ]
        # If no direct-growth results, return all
        if not filtered:
            filtered = results[:10]

        _set_cached(cache_key, filtered[:10])
        return filtered[:10]
    except Exception as e:
        logger.warning(f"MFAPI search failed for '{query}': {e}")
        return []


def get_fd_rates() -> dict:
    """Get current FD and savings scheme interest rates.

    Returns manually maintained rates (updated periodically).
    These change infrequently (RBI policy changes every 2-3 months).
    """
    return {
        "rbi_repo_rate": {"name": "RBI Repo Rate", "rate": _FD_RATES["rbi_repo_rate"], "unit": "%"},
        "sbi_fd_1yr": {"name": "SBI FD (1 year)", "rate": _FD_RATES["sbi_fd_1yr"], "unit": "%"},
        "sbi_fd_3yr": {"name": "SBI FD (3 years)", "rate": _FD_RATES["sbi_fd_3yr"], "unit": "%"},
        "sbi_fd_5yr": {"name": "SBI FD (5 years)", "rate": _FD_RATES["sbi_fd_5yr"], "unit": "%"},
        "ppf": {"name": "PPF (Public Provident Fund)", "rate": _FD_RATES["ppf_rate"], "unit": "%"},
        "sukanya_samriddhi": {"name": "Sukanya Samriddhi Yojana", "rate": _FD_RATES["sukanya_samriddhi"], "unit": "%"},
        "nsc": {"name": "National Savings Certificate", "rate": _FD_RATES["nsc_rate"], "unit": "%"},
        "epf": {"name": "EPF (Employee Provident Fund)", "rate": _FD_RATES["epf_rate"], "unit": "%"},
        "scss": {"name": "Senior Citizen Savings Scheme", "rate": _FD_RATES["senior_citizen_savings"], "unit": "%"},
        "post_office": {"name": "Post Office Savings Account", "rate": _FD_RATES["post_office_savings"], "unit": "%"},
    }


def get_nse_indices() -> list[dict]:
    """Get broad NSE index data directly from NSE India (free, no key).

    Returns top indices with prices and % changes.
    Cached for 5 minutes.
    """
    cached = _get_cached("nse_indices", 300)
    if cached:
        return cached

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json",
        })
        # Get cookies from homepage first (required by NSE)
        session.get("https://www.nseindia.com", timeout=10)

        r = session.get("https://www.nseindia.com/api/allIndices", timeout=10)
        if r.status_code != 200:
            return []

        data = r.json().get("data", [])
        result = []
        for idx in data[:15]:  # Top 15 indices
            result.append({
                "name": idx.get("index", ""),
                "price": idx.get("last", 0),
                "change": idx.get("variation", 0),
                "change_pct": idx.get("percentChange", 0),
                "open": idx.get("open", 0),
                "high": idx.get("high", 0),
                "low": idx.get("low", 0),
                "prev_close": idx.get("previousClose", 0),
            })

        if result:
            _set_cached("nse_indices", result)
        return result
    except Exception as e:
        logger.warning(f"NSE indices fetch failed: {e}")
        return []


# ──────────────────────── Composite Market Snapshot ────────────────────────

def get_market_snapshot() -> dict:
    """Get a comprehensive market snapshot — all key data in one call.

    Returns a dict with indices, gold, forex, and interest rates.
    Used by the market prefetch system for the hourly briefing.
    Individual data sources are cached separately, so this is fast
    on repeated calls.
    """
    snapshot = {}

    # Indices
    indices = get_indices()
    if indices:
        snapshot["indices"] = indices

    # Gold price in INR
    gold = get_gold_price_inr()
    if gold:
        snapshot["gold"] = gold

    # Forex
    forex = get_forex()
    if forex:
        snapshot["forex"] = forex

    # Commodities
    commodities = get_commodities()
    if commodities:
        snapshot["commodities"] = commodities

    # FD/savings rates
    snapshot["rates"] = get_fd_rates()

    return snapshot


def format_market_snapshot(snapshot: dict) -> str:
    """Format a market snapshot into a compact text string for LLM context.

    This replaces the old DDG-based prefetch with structured, reliable data.
    """
    from datetime import date
    today = date.today().strftime("%d %B %Y")
    lines = [f"LIVE MARKET DATA ({today}):"]

    # Indices
    indices = snapshot.get("indices", {})
    if indices:
        lines.append("  [Indices]")
        for key, data in indices.items():
            sign = "+" if data["change_pct"] >= 0 else ""
            lines.append(f"    • {data['name']}: {data['price']:,.2f} ({sign}{data['change_pct']:.2f}%)")

    # Gold
    gold = snapshot.get("gold")
    if gold:
        lines.append("  [Gold]")
        sign = "+" if gold["change_pct"] >= 0 else ""
        lines.append(f"    • 24K Gold: ₹{gold['price_per_10g_24k']:,.0f}/10g | ₹{gold['price_per_gram_24k']:,.0f}/g ({sign}{gold['change_pct']:.2f}%)")
        lines.append(f"    • 22K Gold: ₹{gold['price_per_10g_22k']:,.0f}/10g | ₹{gold['price_per_gram_22k']:,.0f}/g")
        lines.append(f"    • 18K Gold: ₹{gold['price_per_10g_18k']:,.0f}/10g | ₹{gold['price_per_gram_18k']:,.0f}/g")
        lines.append(f"    • Gold (intl): ${gold['price_per_oz_usd']:,.2f}/oz")

    # Forex
    forex = snapshot.get("forex", {})
    if forex:
        lines.append("  [Forex]")
        for key, data in forex.items():
            sign = "+" if data["change_pct"] >= 0 else ""
            lines.append(f"    • {data['name']}: ₹{data['price']:.2f} ({sign}{data['change_pct']:.2f}%)")

    # Commodities (exclude gold — already shown separately)
    commodities = snapshot.get("commodities", {})
    other_commodities = {k: v for k, v in commodities.items() if "gold" not in k}
    if other_commodities:
        lines.append("  [Commodities]")
        for key, data in other_commodities.items():
            sign = "+" if data["change_pct"] >= 0 else ""
            lines.append(f"    • {data['name']}: ${data['price']:,.2f} {data['unit']} ({sign}{data['change_pct']:.2f}%)")

    # Interest rates (compact)
    rates = snapshot.get("rates", {})
    if rates:
        lines.append("  [Key Rates]")
        key_rates = ["rbi_repo_rate", "ppf", "epf", "sbi_fd_1yr"]
        for rk in key_rates:
            if rk in rates:
                lines.append(f"    • {rates[rk]['name']}: {rates[rk]['rate']}%")

    return "\n".join(lines)
