"""Stock Market Analyst Agent - India focused."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from agents.base import BaseAgent, fmt_inr
from tools.market_data import (
    get_stock_price, get_company_financials, get_stock_history,
    get_multiple_stocks, get_market_indices, get_sector_performance,
    get_nifty50_stocks, get_gold_silver_price,
    stock_fundamental_analysis,
    format_number, format_pct,
)
from tools.web_search import search_stock_news
from tools.financial_calc import cagr, sip_calculator


class StockAnalystAgent(BaseAgent):
    name = "Stock Market Analyst (NSE/BSE)"
    icon = "📈"
    description = "Expert Indian & global stock market analysis, Nifty/Sensex, company fundamentals, sectoral analysis"

    system_prompt = """Indian equity analyst (NSE/BSE). Explain your analysis clearly so non-experts understand the reasoning.

APPROACH: Use PRE-COMPUTED metrics → Assess valuation → BULLISH/BEARISH/NEUTRAL view → Action.
- P/E vs PEG, not standalone. Nifty avg 20-22×. Div >2%=good, >4%=check trap. ROE>15%=quality. D/E>1(non-BFSI)=caution.
- 52W high+volume=strength. 52W low=verify. Large ≤10%, Mid 5-10%, Small ≤5%.
- FOMO→SIP entry. Panic→recovery data. Profit booking→LTCG vs STCG. Large sum→stagger 3-6mo.
- Tax: LTCG 12.5% >₹1.25L (>1yr). STCG 20% (<1yr). Harvest ₹1.25L/yr.

FORMAT: Use PRE-COMPUTED data. ₹ Lakhs/Crores. Explain what metrics mean (e.g. why P/E matters). Use tables for comparisons. End with: (1) clear view + conviction (2) specific action (3) risk to watch."""

    def gather_context(self, query: str) -> str:
        context_parts = []
        # ── Inject relevant financial knowledge ──
        knowledge = self.get_knowledge_context(query)
        if knowledge:
            context_parts.append(knowledge)
        tickers = self.extract_tickers(query)

        # Extensive Indian company name to ticker mapping
        name_map = {
            # Indian Large Caps
            "reliance": "RELIANCE.NS", "ril": "RELIANCE.NS",
            "tcs": "TCS.NS", "tata consultancy": "TCS.NS",
            "infosys": "INFY.NS", "infy": "INFY.NS",
            "hdfc bank": "HDFCBANK.NS", "hdfc": "HDFCBANK.NS", "hdfcbank": "HDFCBANK.NS",
            "icici bank": "ICICIBANK.NS", "icici": "ICICIBANK.NS",
            "sbi": "SBIN.NS", "state bank": "SBIN.NS",
            "kotak": "KOTAKBANK.NS", "kotak bank": "KOTAKBANK.NS",
            "axis bank": "AXISBANK.NS", "axis": "AXISBANK.NS",
            "hindustan unilever": "HINDUNILVR.NS", "hul": "HINDUNILVR.NS",
            "itc": "ITC.NS",
            "bharti airtel": "BHARTIARTL.NS", "airtel": "BHARTIARTL.NS",
            "bajaj finance": "BAJFINANCE.NS", "bajfinance": "BAJFINANCE.NS",
            "bajaj finserv": "BAJAJFINSV.NS",
            "maruti": "MARUTI.NS", "maruti suzuki": "MARUTI.NS",
            "asian paints": "ASIANPAINT.NS",
            "larsen": "LT.NS", "l&t": "LT.NS", "larsen toubro": "LT.NS",
            "hcl tech": "HCLTECH.NS", "hcltech": "HCLTECH.NS",
            "tata motors": "TATAMOTORS.NS",
            "tata steel": "TATASTEEL.NS",
            "sun pharma": "SUNPHARMA.NS", "sunpharma": "SUNPHARMA.NS",
            "titan": "TITAN.NS",
            "wipro": "WIPRO.NS",
            "ntpc": "NTPC.NS",
            "power grid": "POWERGRID.NS",
            "ongc": "ONGC.NS",
            "coal india": "COALINDIA.NS",
            "adani enterprises": "ADANIENT.NS", "adani": "ADANIENT.NS",
            "adani ports": "ADANIPORTS.NS",
            "adani green": "ADANIGREEN.NS",
            "tech mahindra": "TECHM.NS",
            "ultracemco": "ULTRACEMCO.NS", "ultratech": "ULTRACEMCO.NS",
            "nestle india": "NESTLEIND.NS", "nestle": "NESTLEIND.NS",
            "britannia": "BRITANNIA.NS",
            "divi's": "DIVISLAB.NS", "divis lab": "DIVISLAB.NS",
            "dr reddy": "DRREDDY.NS", "drreddy": "DRREDDY.NS",
            "cipla": "CIPLA.NS",
            "m&m": "M&M.NS", "mahindra": "M&M.NS",
            "bajaj auto": "BAJAJ-AUTO.NS",
            "hero motocorp": "HEROMOTOCO.NS", "hero": "HEROMOTOCO.NS",
            "indusind bank": "INDUSINDBK.NS", "indusind": "INDUSINDBK.NS",
            "zomato": "ZOMATO.NS",
            "paytm": "PAYTM.NS",
            "nykaa": "NYKAA.NS",
            "policybazaar": "POLICYBZR.NS",
            "dmart": "DMART.NS", "avenue supermarts": "DMART.NS",
            "irctc": "IRCTC.NS",
            "tata power": "TATAPOWER.NS",
            "jsw steel": "JSWSTEEL.NS",
            "hindalco": "HINDALCO.NS",
            "vedanta": "VEDL.NS",
            "dabur": "DABUR.NS",
            "marico": "MARICO.NS",
            "pidilite": "PIDILITIND.NS",
            "havells": "HAVELLS.NS",
            "dixon": "DIXON.NS",
            # US stocks (also supported)
            "apple": "AAPL", "google": "GOOGL", "alphabet": "GOOGL",
            "microsoft": "MSFT", "amazon": "AMZN", "meta": "META",
            "tesla": "TSLA", "nvidia": "NVDA", "netflix": "NFLX",
        }
        query_lower = query.lower()
        for name, ticker in name_map.items():
            if name in query_lower and ticker not in tickers:
                tickers.append(ticker)

        # Auto-add .NS suffix for plain Indian tickers
        processed_tickers = []
        for t in tickers:
            if t and "." not in t and "^" not in t and "=" not in t:
                processed_tickers.append(f"{t}.NS")
                processed_tickers.append(t)
            else:
                processed_tickers.append(t)
        tickers = processed_tickers

        if tickers:
            # Analyze up to 3 tickers in parallel
            with ThreadPoolExecutor(max_workers=3, thread_name_prefix="stock") as pool:
                analysis_futures = {pool.submit(stock_fundamental_analysis, t): t
                                    for t in tickers[:3]}
            # Collect results preserving order
            analysis_map = {}
            for future in as_completed(analysis_futures):
                t = analysis_futures[future]
                try:
                    analysis_map[t] = future.result()
                except Exception:
                    pass

            for t in tickers[:3]:
                analysis = analysis_map.get(t)
                if not analysis or "error" in analysis:
                    continue

                cur_price = analysis.get("price")
                name = analysis.get("name", t)

                # ── Price Summary ──
                lines = [f"STOCK: {name} ({t})"]
                if cur_price:
                    lines.append(f"  Price: ₹{cur_price:,.2f}")
                chg = analysis.get("change_pct")
                if chg is not None:
                    lines.append(f"  Day Change: {chg:+.2f}%")
                lo52 = analysis.get("52w_low")
                hi52 = analysis.get("52w_high")
                if lo52 and hi52:
                    lines.append(f"  52W Range: ₹{lo52:,.2f} – ₹{hi52:,.2f}")
                if cur_price and hi52 and hi52 > 0:
                    off_high = ((cur_price - hi52) / hi52) * 100
                    lines.append(f"  From 52W High: {off_high:.1f}%")
                mkt_cap = analysis.get("market_cap")
                if mkt_cap:
                    lines.append(f"  Market Cap: {fmt_inr(mkt_cap)}")
                sector = analysis.get("sector")
                industry = analysis.get("industry")
                if sector:
                    lines.append(f"  Sector: {sector}" + (f" / {industry}" if industry else ""))
                context_parts.append("\n".join(lines))

                # ── Fundamentals ──
                val_lines = [f"FUNDAMENTALS for {t}:"]
                pe = analysis.get("pe_ratio")
                if pe and isinstance(pe, (int, float)):
                    verdict = "UNDERVALUED" if pe < 15 else "FAIR" if pe < 25 else "PREMIUM" if pe < 40 else "EXPENSIVE"
                    val_lines.append(f"  P/E: {pe:.1f} → {verdict} (Nifty avg 20-22×)")
                fwd_pe = analysis.get("forward_pe")
                if fwd_pe and isinstance(fwd_pe, (int, float)):
                    val_lines.append(f"  Forward P/E: {fwd_pe:.1f}")
                peg = analysis.get("peg_ratio")
                if peg and isinstance(peg, (int, float)):
                    peg_label = "undervalued" if peg < 1 else "fair" if peg < 2 else "overvalued"
                    val_lines.append(f"  PEG Ratio: {peg:.2f} → {peg_label}")
                ptb = analysis.get("price_to_book")
                if ptb and isinstance(ptb, (int, float)):
                    val_lines.append(f"  P/B: {ptb:.2f}")
                ev_ebitda = analysis.get("ev_to_ebitda")
                if ev_ebitda and isinstance(ev_ebitda, (int, float)):
                    val_lines.append(f"  EV/EBITDA: {ev_ebitda:.1f}")

                eps = analysis.get("eps")
                if eps and isinstance(eps, (int, float)):
                    val_lines.append(f"  EPS: ₹{eps:.2f}")
                eg = analysis.get("earnings_growth")
                if eg and isinstance(eg, (int, float)):
                    val_lines.append(f"  Earnings Growth: {eg*100:.1f}%" if abs(eg) < 5 else f"  Earnings Growth: {eg:.1f}%")
                rg = analysis.get("revenue_growth")
                if rg and isinstance(rg, (int, float)):
                    val_lines.append(f"  Revenue Growth: {rg*100:.1f}%" if abs(rg) < 5 else f"  Revenue Growth: {rg:.1f}%")

                roe = analysis.get("roe")
                if roe and isinstance(roe, (int, float)):
                    roe_pct = roe * 100 if abs(roe) < 1 else roe
                    val_lines.append(f"  ROE: {roe_pct:.1f}% ({'Excellent' if roe_pct > 20 else 'Good' if roe_pct > 15 else 'Avg' if roe_pct > 10 else 'Low'})")
                de = analysis.get("debt_to_equity")
                if de and isinstance(de, (int, float)):
                    val_lines.append(f"  D/E: {de:.0f}% ({'Low risk' if de < 50 else 'Moderate' if de < 100 else 'High'})")
                cr = analysis.get("current_ratio")
                if cr and isinstance(cr, (int, float)):
                    val_lines.append(f"  Current Ratio: {cr:.2f}")
                fcf = analysis.get("free_cashflow")
                if fcf and isinstance(fcf, (int, float)):
                    val_lines.append(f"  Free Cash Flow: {fmt_inr(fcf)}")

                div_yield = analysis.get("dividend_yield")
                if div_yield and isinstance(div_yield, (int, float)) and div_yield > 0:
                    dy = div_yield * 100 if div_yield < 1 else div_yield
                    val_lines.append(f"  Dividend Yield: {dy:.2f}%")
                payout = analysis.get("payout_ratio")
                if payout and isinstance(payout, (int, float)):
                    val_lines.append(f"  Payout Ratio: {payout*100:.1f}%" if payout < 5 else f"  Payout Ratio: {payout:.1f}%")

                beta = analysis.get("beta")
                if beta and isinstance(beta, (int, float)):
                    val_lines.append(f"  Beta: {beta:.2f} ({'Defensive' if beta < 0.8 else 'Market-like' if beta < 1.2 else 'Aggressive'})")

                rec = analysis.get("recommendation")
                target = analysis.get("target_price")
                if rec:
                    val_lines.append(f"  Analyst Recommendation: {rec.upper()}")
                if target and cur_price:
                    upside = ((target - cur_price) / cur_price) * 100
                    val_lines.append(f"  Target Price: ₹{target:,.0f} ({upside:+.1f}%)")

                if len(val_lines) > 1:
                    context_parts.append("\n".join(val_lines))

                # ── Intrinsic Value ──
                graham = analysis.get("graham_number")
                ddm = analysis.get("ddm_value")
                if graham or ddm:
                    iv_lines = [f"INTRINSIC VALUE ESTIMATES for {t}:"]
                    if graham:
                        margin = ((graham - cur_price) / cur_price) * 100 if cur_price else 0
                        iv_lines.append(f"  Graham Number: ₹{graham:,.0f} ({"+ " if margin > 0 else ""}{margin:.1f}% vs CMP)")
                    if ddm:
                        iv_lines.append(f"  Dividend Discount Model: ₹{ddm:,.0f}")
                    context_parts.append("\n".join(iv_lines))

                # ── AI Signals ──
                signals = analysis.get("signals", [])
                verdict = analysis.get("verdict", "")
                if signals:
                    sig_lines = [f"ANALYSIS SIGNALS for {t} → {verdict}:"]
                    for s in signals:
                        sig_lines.append(f"  ✦ {s}")
                    context_parts.append("\n".join(sig_lines))

            # Pre-compute: if user mentioned an investment amount
            numbers = self.extract_numbers(query)
            inv_amounts = [n for n in numbers if n >= 1000]
            if inv_amounts and tickers:
                amt = inv_amounts[0]
                t = tickers[0]
                price_data = get_stock_price(t)
                cur_price = price_data.get("price")
                if cur_price and cur_price > 0:
                    shares = int(amt / cur_price)
                    actual_cost = shares * cur_price
                    context_parts.append(
                        f"INVESTMENT CALC: {fmt_inr(amt)} in {t} → "
                        f"{shares} shares @ ₹{cur_price:.2f} = {fmt_inr(actual_cost)}"
                    )

            # Get news for the first ticker
            news = search_stock_news(tickers[0])
            if news and "error" not in news[0]:
                context_parts.append(f"LATEST NEWS for {tickers[0]}:")
                for n in news[:3]:
                    context_parts.append(f"  • {n.get('title', '')}: {n.get('snippet', '')}")

        # ── Parallel fetch: market overview, sectors, news, live data ──
        overview_keywords = ["market", "index", "indices", "nifty", "sensex", "s&p", "dow", "nasdaq"]
        need_indices = any(kw in query_lower for kw in overview_keywords) and not tickers
        need_sectors = "sector" in query_lower
        # Always fetch live market data (gold/forex/crude) if keywords match
        parallel_tasks = {}
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="stock_ctx") as pool:
            if need_indices:
                parallel_tasks[pool.submit(get_market_indices)] = "indices"
            if need_sectors:
                parallel_tasks[pool.submit(get_sector_performance)] = "sectors"
            parallel_tasks[pool.submit(self._auto_market_data, query)] = "live_data"

        for future in as_completed(parallel_tasks):
            tag = parallel_tasks[future]
            try:
                result = future.result()
                if tag == "indices" and isinstance(result, list):
                    idx_lines = ["MARKET INDICES:"]
                    for idx_data in result:
                        if isinstance(idx_data, dict) and "error" not in idx_data:
                            idx_name = idx_data.get("name", idx_data.get("ticker", ""))
                            price = idx_data.get("price", "N/A")
                            change = idx_data.get("change_pct", 0)
                            if isinstance(price, (int, float)):
                                idx_lines.append(f"  {idx_name}: {price:,.2f} ({change:+.2f}%)")
                            else:
                                idx_lines.append(f"  {idx_name}: {price}")
                    if len(idx_lines) > 1:
                        context_parts.append("\n".join(idx_lines))
                elif tag == "sectors" and isinstance(result, dict):
                    sec_lines = ["SECTOR PERFORMANCE:"]
                    for sec_name, sec_data in result.items():
                        if isinstance(sec_data, dict):
                            change = sec_data.get("change_pct", 0)
                            sec_lines.append(f"  {sec_name}: {change:+.2f}%")
                    if len(sec_lines) > 1:
                        context_parts.append("\n".join(sec_lines))
                elif tag == "live_data" and result:
                    context_parts.append(f"LIVE MARKET DATA:\n{result}")
            except Exception:
                pass

        # News/web fallback for general stock queries
        if not tickers and not context_parts:
            web_results = self.web_lookup(f"{self.extract_search_keywords(query)} Indian stock market analysis")
            if web_results:
                context_parts.append(f"MARKET OVERVIEW:\n{web_results}")

        return "\n\n".join(context_parts)
