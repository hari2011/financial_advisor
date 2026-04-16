"""Market data tools using yfinance with parallel fetching."""
import logging
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("financegpt.tools.market")

# Thread pool for yfinance calls (yfinance is thread-safe — each Ticker
# creates its own HTTP session). Shared pool avoids spawning threads per call.
_yf_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="yfinance")


def get_stock_price(ticker: str) -> dict:
    """Get current stock price and key metrics."""
    try:
        logger.info(f"Fetching price for {ticker}")
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="5d")
        if hist.empty:
            return {"error": f"No data found for ticker '{ticker}'"}

        current = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
        change = current - prev
        change_pct = (change / prev) * 100

        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", info.get("shortName", ticker)),
            "price": round(current, 2),
            "previous_close": round(prev, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "open": info.get("open"),
            "volume": info.get("volume"),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "peg_ratio": info.get("pegRatio"),
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "book_value": info.get("bookValue"),
            "price_to_book": info.get("priceToBook"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "50d_avg": info.get("fiftyDayAverage"),
            "200d_avg": info.get("twoHundredDayAverage"),
            "avg_volume": info.get("averageVolume"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "beta": info.get("beta"),
        }
    except Exception as e:
        return {"error": str(e)}


def get_stock_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Get historical price data."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception:
        return pd.DataFrame()


def get_company_financials(ticker: str) -> dict:
    """Get company financial statements summary with comprehensive fundamentals."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker),
            # Valuation
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "enterprise_value": info.get("enterpriseValue"),
            "ev_to_ebitda": info.get("enterpriseToEbitda"),
            "ev_to_revenue": info.get("enterpriseToRevenue"),
            # Profitability
            "revenue": info.get("totalRevenue"),
            "revenue_growth": info.get("revenueGrowth"),
            "gross_profit": info.get("grossProfits"),
            "operating_margin": info.get("operatingMargins"),
            "profit_margin": info.get("profitMargins"),
            "ebitda": info.get("ebitda"),
            "net_income": info.get("netIncomeToCommon"),
            "earnings_growth": info.get("earningsGrowth"),
            "eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            # Returns & Efficiency
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            # Balance Sheet
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "book_value": info.get("bookValue"),
            "total_debt": info.get("totalDebt"),
            "total_cash": info.get("totalCash"),
            "free_cashflow": info.get("freeCashflow"),
            "operating_cashflow": info.get("operatingCashflow"),
            # Dividends
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            # Analyst
            "recommendation": info.get("recommendationKey"),
            "target_price": info.get("targetMeanPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "analyst_count": info.get("numberOfAnalystOpinions"),
            # Beta & Risk
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception as e:
        return {"error": str(e)}


def get_multiple_stocks(tickers: list) -> list:
    """Get price data for multiple tickers (parallel)."""
    futures = {_yf_pool.submit(get_stock_price, t.strip()): t for t in tickers}
    results = []
    for future in as_completed(futures):
        results.append(future.result())
    # Preserve original order
    ticker_to_result = {r.get("ticker", "").upper(): r for r in results if isinstance(r, dict)}
    ordered = []
    for t in tickers:
        key = t.strip().upper()
        ordered.append(ticker_to_result.get(key, {"error": f"No data for {t}"}))
    return ordered


def get_crypto_price(symbol: str) -> dict:
    """Get cryptocurrency price data."""
    crypto_ticker = f"{symbol.upper()}-USD"
    return get_stock_price(crypto_ticker)


def get_forex_rate(from_currency: str, to_currency: str) -> dict:
    """Get forex exchange rate."""
    ticker = f"{from_currency.upper()}{to_currency.upper()}=X"
    try:
        fx = yf.Ticker(ticker)
        hist = fx.history(period="5d")
        if hist.empty:
            return {"error": f"No forex data for {from_currency}/{to_currency}"}
        rate = hist["Close"].iloc[-1]
        return {
            "pair": f"{from_currency.upper()}/{to_currency.upper()}",
            "rate": round(rate, 4),
            "date": str(hist.index[-1].date()),
        }
    except Exception as e:
        return {"error": str(e)}


def get_market_indices() -> list:
    """Get major market indices (parallel, Indian markets prioritized)."""
    indices = {
        "^NSEI": "Nifty 50",
        "^BSESN": "Sensex",
        "^NSEBANK": "Bank Nifty",
        "^CNXIT": "Nifty IT",
        "^GSPC": "S&P 500",
        "^DJI": "Dow Jones",
        "^IXIC": "NASDAQ",
    }
    futures = {_yf_pool.submit(get_stock_price, ticker): name
               for ticker, name in indices.items()}
    results = []
    for future in as_completed(futures):
        name = futures[future]
        data = future.result()
        if "error" not in data:
            data["name"] = name
        results.append(data)
    return results


def get_sector_performance() -> dict:
    """Get Nifty sectoral indices and global sector ETFs."""
    sectors = {
        # Indian Nifty Sectoral Indices
        "^CNXAUTO": "Nifty Auto",
        "^CNXBANK": "Nifty Bank",
        "^CNXIT": "Nifty IT",
        "^CNXPHARMA": "Nifty Pharma",
        "^CNXFMCG": "Nifty FMCG",
        "^CNXMETAL": "Nifty Metal",
        "^CNXREALTY": "Nifty Realty",
        "^CNXENERGY": "Nifty Energy",
        # Global sector ETFs for comparison
        "XLK": "US Technology",
        "XLF": "US Financials",
    }
    futures = {_yf_pool.submit(get_stock_price, etf): sector
               for etf, sector in sectors.items()}
    results = {}
    for future in as_completed(futures):
        sector = futures[future]
        data = future.result()
        if "error" not in data:
            results[sector] = {
                "price": data["price"],
                "change_pct": data["change_pct"],
            }
    return results


def search_tickers(query: str) -> list:
    """Search for stock tickers matching a query."""
    try:
        results = yf.Tickers(query)
        return [query.upper()]
    except Exception:
        return []


def get_nifty50_stocks() -> list:
    """Get data for top Nifty 50 constituents."""
    nifty50_tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
        "HCLTECH.NS", "TATAMOTORS.NS", "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS",
    ]
    return get_multiple_stocks(nifty50_tickers)


def get_indian_mutual_fund_navs(fund_names: list) -> list:
    """Search for Indian mutual fund data via web."""
    from tools.web_search import web_search
    results = []
    for name in fund_names[:5]:
        data = web_search(f"{name} mutual fund NAV latest India", max_results=2)
        results.append({"fund": name, "search_results": data})
    return results


def get_gold_silver_price() -> dict:
    """Get gold and silver prices (useful for Indian investors)."""
    gold_f = _yf_pool.submit(get_stock_price, "GC=F")
    silver_f = _yf_pool.submit(get_stock_price, "SI=F")
    usdinr_f = _yf_pool.submit(get_forex_rate, "USD", "INR")
    gold = gold_f.result()
    silver = silver_f.result()
    usdinr = usdinr_f.result()
    return {
        "gold_usd": gold.get("price") if "error" not in gold else None,
        "silver_usd": silver.get("price") if "error" not in silver else None,
        "usd_inr_rate": usdinr.get("rate") if "error" not in usdinr else None,
    }


def format_number(num, currency="INR") -> str:
    """Format large numbers for display in Indian (lakhs/crores) or Western system."""
    if num is None:
        return "N/A"
    if currency == "INR" or currency == "\u20b9":
        # Indian number system: Lakhs and Crores
        if abs(num) >= 1e12:
            return f"\u20b9{num/1e7/1e5:.2f} Lakh Cr"
        if abs(num) >= 1e7:
            return f"\u20b9{num/1e7:.2f} Cr"
        if abs(num) >= 1e5:
            return f"\u20b9{num/1e5:.2f} L"
        if abs(num) >= 1e3:
            return f"\u20b9{num/1e3:.2f}K"
        return f"\u20b9{num:,.2f}"
    else:
        if abs(num) >= 1e12:
            return f"${num/1e12:.2f}T"
        if abs(num) >= 1e9:
            return f"${num/1e9:.2f}B"
        if abs(num) >= 1e6:
            return f"${num/1e6:.2f}M"
        return f"${num:,.2f}"


def format_pct(num) -> str:
    """Format percentage."""
    if num is None:
        return "N/A"
    return f"{num*100:.2f}%" if abs(num) < 1 else f"{num:.2f}%"


# ── Stock Analysis Calculators ──

def graham_number(eps: float, book_value: float) -> float | None:
    """Calculate Graham Number (intrinsic value) = sqrt(22.5 × EPS × BVPS).
    Benjamin Graham's formula for fair value of a stock.
    """
    if eps is None or book_value is None or eps <= 0 or book_value <= 0:
        return None
    return round((22.5 * eps * book_value) ** 0.5, 2)


def peg_ratio(pe: float, earnings_growth: float) -> float | None:
    """PEG Ratio = P/E ÷ Earnings Growth Rate. <1 = undervalued, >2 = overvalued."""
    if pe is None or earnings_growth is None or earnings_growth <= 0:
        return None
    growth_pct = earnings_growth * 100 if earnings_growth < 1 else earnings_growth
    return round(pe / growth_pct, 2) if growth_pct > 0 else None


def dividend_discount_value(dividend_rate: float, required_return: float = 0.12,
                            growth_rate: float = 0.06) -> float | None:
    """Gordon Growth Model: Intrinsic Value = D₁ / (r - g).
    Default: 12% required return, 6% dividend growth (conservative for India).
    """
    if dividend_rate is None or dividend_rate <= 0:
        return None
    if required_return <= growth_rate:
        return None
    d1 = dividend_rate * (1 + growth_rate)
    return round(d1 / (required_return - growth_rate), 2)


def stock_fundamental_analysis(ticker: str) -> dict:
    """Run comprehensive fundamental analysis on a stock.
    Combines price data, financials, and computed valuations.
    """
    price_f = _yf_pool.submit(get_stock_price, ticker)
    fin_f = _yf_pool.submit(get_company_financials, ticker)
    price = price_f.result()
    fin = fin_f.result()

    if "error" in price:
        return price
    if "error" in fin:
        fin = {}

    cur_price = price.get("price", 0)
    eps = price.get("eps") or fin.get("eps")
    bv = price.get("book_value") or fin.get("book_value")
    pe = price.get("pe_ratio") or fin.get("pe_ratio")
    fwd_pe = price.get("forward_pe") or fin.get("forward_pe")
    div_yield = price.get("dividend_yield") or fin.get("dividend_yield")
    div_rate = price.get("dividend_rate") or fin.get("dividend_rate")

    # yfinance sometimes returns dividendYield with wrong scale (e.g. 0.42 instead
    # of 0.0042). Sanity-check: if yield > 20% and we have rate+price, recalculate.
    if div_yield and cur_price and div_rate:
        if div_yield > 0.20:  # Looks wrong — recalculate
            div_yield = div_rate / cur_price

    roe = fin.get("return_on_equity")
    de = fin.get("debt_to_equity")
    eg = fin.get("earnings_growth")
    rg = fin.get("revenue_growth")
    beta_val = price.get("beta") or fin.get("beta")
    hi52 = price.get("52w_high")
    lo52 = price.get("52w_low")
    target = fin.get("target_price")

    # Computed metrics
    graham = graham_number(eps, bv) if eps and bv else None
    computed_peg = peg_ratio(pe, eg) if pe and eg else price.get("peg_ratio")
    ddm_val = dividend_discount_value(div_rate) if div_rate else None

    # Valuation signals
    signals = []
    if pe:
        if pe < 15:
            signals.append(f"Low P/E ({pe:.1f}× vs Nifty ~22×) — potentially undervalued")
        elif pe > 40:
            signals.append(f"High P/E ({pe:.1f}×) — premium/overvalued; needs high growth to justify")
        else:
            signals.append(f"P/E {pe:.1f}× — {'fair' if pe < 25 else 'above avg'} vs Nifty ~22×")

    if computed_peg:
        if computed_peg < 1:
            signals.append(f"PEG {computed_peg:.2f} — undervalued relative to growth")
        elif computed_peg > 2:
            signals.append(f"PEG {computed_peg:.2f} — overvalued relative to growth")

    if graham and cur_price:
        margin = ((graham - cur_price) / cur_price) * 100
        if margin > 20:
            signals.append(f"Graham Number ₹{graham:,.0f} — {margin:.0f}% upside (value buy)")
        elif margin < -20:
            signals.append(f"Graham Number ₹{graham:,.0f} — trading {abs(margin):.0f}% above intrinsic value")

    if roe and isinstance(roe, (int, float)):
        roe_pct = roe * 100 if abs(roe) < 1 else roe
        if roe_pct > 20:
            signals.append(f"ROE {roe_pct:.1f}% — excellent capital efficiency")
        elif roe_pct > 15:
            signals.append(f"ROE {roe_pct:.1f}% — good")
        elif roe_pct < 10:
            signals.append(f"ROE {roe_pct:.1f}% — below average")

    if de and isinstance(de, (int, float)):
        if de > 100:
            signals.append(f"D/E {de:.0f}% — high leverage, risky")
        elif de < 30:
            signals.append(f"D/E {de:.0f}% — conservatively financed")

    if div_yield and isinstance(div_yield, (int, float)):
        dy = div_yield * 100 if div_yield < 1 else div_yield
        if dy > 4:
            signals.append(f"Dividend Yield {dy:.2f}% — high (check if sustainable)")
        elif dy > 2:
            signals.append(f"Dividend Yield {dy:.2f}% — good for Indian market")

    if hi52 and cur_price and hi52 > 0:
        from_high = ((cur_price - hi52) / hi52) * 100
        if from_high > -5:
            signals.append(f"Near 52W high — strength/momentum")
        elif from_high < -30:
            signals.append(f"{abs(from_high):.0f}% below 52W high — check for recovery potential")

    if target and cur_price and target > 0:
        upside = ((target - cur_price) / cur_price) * 100
        signals.append(f"Analyst target ₹{target:,.0f} ({upside:+.1f}% from CMP)")

    # Overall verdict
    bullish = sum(1 for s in signals if any(w in s.lower() for w in
                  ["undervalued", "upside", "value buy", "excellent", "good", "strength"]))
    bearish = sum(1 for s in signals if any(w in s.lower() for w in
                  ["overvalued", "high leverage", "risky", "expensive", "below average"]))
    if bullish > bearish + 1:
        verdict = "BULLISH"
    elif bearish > bullish + 1:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    return {
        "ticker": ticker.upper(),
        "name": price.get("name", ticker),
        "price": cur_price,
        "change_pct": price.get("change_pct"),
        "market_cap": price.get("market_cap"),
        "sector": price.get("sector"),
        "industry": price.get("industry"),
        # Valuation
        "pe_ratio": pe,
        "forward_pe": fwd_pe,
        "peg_ratio": computed_peg,
        "price_to_book": price.get("price_to_book") or fin.get("price_to_book"),
        "ev_to_ebitda": fin.get("ev_to_ebitda"),
        # Intrinsic value
        "graham_number": graham,
        "ddm_value": ddm_val,
        # Growth
        "eps": eps,
        "earnings_growth": eg,
        "revenue_growth": rg,
        # Quality
        "roe": roe,
        "debt_to_equity": de,
        "current_ratio": fin.get("current_ratio"),
        "free_cashflow": fin.get("free_cashflow"),
        # Income
        "dividend_yield": div_yield,
        "dividend_rate": div_rate,
        "payout_ratio": fin.get("payout_ratio"),
        # Range/Risk
        "52w_high": hi52,
        "52w_low": lo52,
        "beta": beta_val,
        "50d_avg": price.get("50d_avg"),
        "200d_avg": price.get("200d_avg"),
        # Analyst
        "recommendation": fin.get("recommendation"),
        "target_price": target,
        "analyst_count": fin.get("analyst_count"),
        # Intelligence
        "signals": signals,
        "verdict": verdict,
    }
