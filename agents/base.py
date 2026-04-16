"""Base agent class for all financial advisor agents."""
import re
import time
import logging
import traceback
from llm.engine import llm
from tools.web_search import web_search, news_search

logger = logging.getLogger("financegpt.agent")


def fmt_inr(amount: float) -> str:
    """Format a number in Indian ₹ notation with Lakhs/Crores label.
    Examples: 2500000 → '₹25,00,000 (25 Lakhs)'
              10000000 → '₹1,00,00,000 (1 Crore)'
              50000 → '₹50,000 (50K)'
              1234 → '₹1,234'
    """
    amount = round(amount)
    abs_amt = abs(amount)
    sign = "-" if amount < 0 else ""

    # Indian comma formatting
    if abs_amt >= 10000000:  # Crores
        s = str(abs_amt)
        # Crore part + lakh part + thousands + rest
        cr_part = s[:-7]
        rest = s[-7:]
        formatted = cr_part + "," + rest[:2] + "," + rest[2:4] + "," + rest[4:]
        cr_val = abs_amt / 10000000
        label = f"{cr_val:.2f}".rstrip("0").rstrip(".") + " Cr"
    elif abs_amt >= 100000:  # Lakhs
        s = str(abs_amt)
        lakh_part = s[:-5]
        rest = s[-5:]
        formatted = lakh_part + "," + rest[:2] + "," + rest[2:]
        lakh_val = abs_amt / 100000
        label = f"{lakh_val:.2f}".rstrip("0").rstrip(".") + " Lakhs"
    elif abs_amt >= 1000:
        s = str(abs_amt)
        formatted = s[:-3] + "," + s[-3:]
        if abs_amt >= 50000:
            label = f"{abs_amt / 1000:.0f}K"
        else:
            label = f"{abs_amt / 1000:.1f}K".rstrip("0").rstrip(".")
        return f"{sign}₹{formatted} ({label})"
    else:
        return f"{sign}₹{abs_amt}"

    return f"{sign}₹{formatted} ({label})"


class BaseAgent:
    name: str = "Base Agent"
    description: str = ""
    system_prompt: str = ""
    icon: str = "🤖"

    def get_knowledge_context(self, query: str, max_sections: int = 4) -> str:
        """Inject relevant Indian financial knowledge based on query topic.
        Uses related-topics cross-referencing so salary queries auto-include
        EPF/gratuity knowledge. Limited to 4 sections (~4000 chars).
        """
        from knowledge.indian_finance import get_relevant_knowledge
        knowledge = get_relevant_knowledge(query, max_sections=max_sections)
        # Hard cap to prevent token budget overflow
        if len(knowledge) > 4500:
            # Trim to last complete line before cap
            knowledge = knowledge[:4500]
            last_newline = knowledge.rfind('\n')
            if last_newline > 3500:
                knowledge = knowledge[:last_newline]
            knowledge += "\n═══ END REFERENCE ═══"
        return knowledge

    def extract_tickers(self, query: str) -> list:
        """Extract stock ticker symbols from query."""
        # Common patterns: $AAPL, AAPL, "apple stock"
        tickers = re.findall(r'\$([A-Z]{1,5})', query.upper())
        tickers += re.findall(r'\b([A-Z]{2,5})\b', query)
        # Filter out common English words
        stopwords = {
            "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
            "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "HAS", "HIS",
            "HOW", "ITS", "LET", "MAY", "NEW", "NOW", "OLD", "SEE",
            "WAY", "WHO", "BOY", "DID", "GET", "HIM", "HIT", "HOT",
            "MAN", "RAN", "SAT", "SHE", "TOP", "TWO", "WHY", "FAR",
            "SIP", "EMI", "TAX", "FEE", "BUY", "PUT", "CALL", "WHAT",
            "WHEN", "WITH", "WILL", "HAVE", "THIS", "THAT", "FROM",
            "THEY", "BEEN", "SAID", "EACH", "MAKE", "LIKE", "LONG",
            "LOOK", "MANY", "SOME", "THAN", "THEM", "THEN", "WERE",
            "MOST", "MUCH", "BEST", "GOOD", "HIGH", "LOW", "RATE",
            "YEAR", "ALSO", "BACK", "OVER", "SUCH", "ONLY", "TELL",
            "VERY", "YOUR", "WANT", "GIVE", "NEED", "HELP", "SHOW",
            "INTO", "JUST", "KNOW", "TAKE", "COME", "COULD", "THINK",
            "ABOUT", "WHICH", "WOULD", "AFTER", "WHERE", "RIGHT",
            "STILL", "FIND", "HERE", "THING", "EVERY", "THOSE",
            "STOCK", "PRICE", "MARKET", "TRADE", "FUND", "BOND",
            "DEBT", "LOAN", "SAVE", "RISK", "PLAN", "INVEST", "MONEY",
        }
        return [t for t in tickers if t not in stopwords and len(t) >= 2]

    def extract_numbers(self, query: str) -> list:
        """Extract numbers from query, understanding Indian notation.
        Handles: 1 lakh, 1L, 1.5L, ₹50K, 2Cr, 1,00,000, 50000, etc.
        Returns numbers normalised to their actual rupee value.
        """
        text = query.lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs ", " ")

        results = []

        # Pattern: number followed by Indian magnitude word/abbreviation
        # Matches: 1lakh, 1 lakh, 1.5 lakhs, 1L, 2.5L, 50k, 1cr, 1crore, 2.5 crores, 12LPA
        mag_pattern = re.compile(
            r'(\d+\.?\d*)\s*'
            r'(crores?|cr'
            r'|lakhs?|lacs?|lpa|lac'
            r'|thousands?'
            r'|[lkc]'
            r')(?![a-zA-Z])',
            re.IGNORECASE
        )
        for match in mag_pattern.finditer(text):
            num = float(match.group(1))
            unit = match.group(2).lower()
            if unit.startswith("cr") or unit == "c":
                results.append(num * 10000000)
            elif unit in ("lpa",):
                # LPA = Lakhs Per Annum — value is in lakhs (annual)
                results.append(num * 100000)
            elif unit.startswith("la") or unit == "l":
                results.append(num * 100000)
            elif unit.startswith("th") or unit == "k":
                results.append(num * 1000)
            # Mark this region as consumed
            text = text[:match.start()] + " " * (match.end() - match.start()) + text[match.end():]

        # Pattern: plain numbers not already consumed (e.g. 50000, 8.5, 20)
        plain_pattern = re.compile(r'(\d+\.?\d*)')
        for match in plain_pattern.finditer(text):
            num = float(match.group(1))
            if num > 0:
                results.append(num)

        return results

    def detect_income_frequency(self, query: str) -> str:
        """Detect whether the user is talking about monthly or annual income.
        Returns 'monthly' or 'annual'. Defaults to 'monthly' (most common in India).
        """
        q = query.lower()
        annual_signals = [
            "per year", "per annum", "/year", "p.a.", "pa ", "annual",
            "yearly", "ctc", "package", "lpa", "salary package",
        ]
        monthly_signals = [
            "per month", "/month", "p.m.", "pm ", "monthly", "/m ",
            "salary", "income", "earn", "take home", "in-hand",
            "hand salary", "per month",
        ]
        annual_score = sum(1 for s in annual_signals if s in q)
        monthly_score = sum(1 for s in monthly_signals if s in q)

        # "lpa" or "ctc" are strong annual signals
        if re.search(r'\b(lpa|ctc)\b', q):
            return "annual"

        if annual_score > monthly_score:
            return "annual"
        # Default to monthly — most Indian users mean monthly when they say salary/income
        return "monthly"

    def normalise_to_monthly(self, amount: float, query: str) -> float:
        """Given an extracted amount and the user query, return monthly figure.
        If amount is annual, divide by 12. Heuristic: amounts > 25 lakh likely annual CTC.
        """
        freq = self.detect_income_frequency(query)
        if freq == "annual":
            return round(amount / 12, 2)
        return amount

    def extract_currencies(self, query: str) -> list:
        """Extract currency codes from query."""
        currencies = re.findall(r'\b(USD|EUR|GBP|JPY|INR|AUD|CAD|CHF|CNY|SGD|HKD)\b',
                                query.upper())
        return currencies

    def extract_search_keywords(self, query: str) -> str:
        """Extract meaningful financial keywords from a natural language query.
        Strips filler/personal words so web searches return relevant results.
        E.g. 'I am 32 with CTC salary of 25 lakhs. I want a home loan'
             → 'home loan salary 25 lakhs'
        """
        q = query.lower()
        # Financial topic words worth keeping in a search query
        _KEEP = {
            "home", "loan", "car", "personal", "education", "gold", "lap",
            "mortgage", "emi", "interest", "rate", "rates", "prepay",
            "mutual", "fund", "funds", "sip", "elss", "index",
            "nifty", "sensex", "stock", "share", "equity", "ipo", "dividend",
            "small", "mid", "large", "cap", "flexi", "multi", "debt", "liquid",
            "hybrid", "balanced", "direct", "plan",
            "tax", "deduction", "regime", "80c", "80d",
            "insurance", "term", "health", "life", "cover", "premium",
            "budget", "savings", "invest", "investment", "portfolio", "allocation",
            "retirement", "pension", "nps", "ppf", "epf", "gratuity",
            "crypto", "bitcoin", "ethereum",
            "fd", "fixed", "deposit", "sgb", "bond",
            "salary", "ctc",
            "india", "indian", "rbi", "sebi", "irdai",
            "best", "top", "comparison", "compare",
            "2024", "2025", "2026",
        }
        words = re.findall(r'[a-z0-9]+', q)
        seen = set()
        keywords = []
        for w in words:
            if w in _KEEP and w not in seen:
                seen.add(w)
                keywords.append(w)
        result = " ".join(keywords[:8])
        return result.strip() if result.strip() else "India finance"

    def web_lookup(self, query: str) -> str:
        """Search the web for additional information."""
        logger.info(f"[{self.name}] Web search: {query[:80]}")
        try:
            results = web_search(query, max_results=3)
            if not results or "error" in results[0]:
                logger.warning(f"[{self.name}] Web search returned no results or error")
                return "No web results found."
            text = ""
            for r in results:
                text += f"• {r.get('title', '')}: {r.get('snippet', '')}\n"
            logger.info(f"[{self.name}] Web search returned {len(results)} results")
            return text
        except Exception as e:
            logger.error(f"[{self.name}] Web search failed: {e}")
            return f"Web search unavailable: {e}"

    def news_lookup(self, query: str) -> str:
        """Get latest news on a topic."""
        logger.info(f"[{self.name}] News search: {query[:80]}")
        try:
            results = news_search(query, max_results=3)
            if not results or "error" in results[0]:
                logger.warning(f"[{self.name}] News search returned no results or error")
                return "No news results found."
            text = ""
            for r in results:
                text += f"• [{r.get('source', '')}] {r.get('title', '')}: {r.get('snippet', '')}\n"
            logger.info(f"[{self.name}] News search returned {len(results)} results")
            return text
        except Exception as e:
            logger.error(f"[{self.name}] News search failed: {e}")
            return f"News search unavailable: {e}"

    def _auto_market_data(self, query: str) -> str:
        """Detect if query needs live market data and fetch relevant prices/rates."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from tools.market_data import get_stock_price, get_forex_rate, get_gold_silver_price

        q = query.lower()
        parts = []

        # Determine which data to fetch
        gold_kw = ["gold", "sona", "sovereign gold", "sgb", "gold rate",
                    "gold price", "jewel", "22 carat", "24 carat", "hallmark"]
        idx_kw = ["nifty", "sensex", "market today", "stock market", "share market",
                  "market crash", "market rally", "bull market", "bear market"]
        fx_kw = ["dollar", "usd", "forex", "exchange rate", "usd/inr",
                 "remittance", "foreign currency", "dollar rate"]
        rate_kw = ["repo rate", "rbi rate", "interest rate", "fd rate",
                   "ppf rate", "current rate", "latest rate", "bank rate",
                   "lending rate", "deposit rate"]
        oil_kw = ["crude", "oil price", "brent", "wti", "petrol price",
                  "diesel price", "fuel price"]

        need_gold = any(w in q for w in gold_kw)
        need_silver = need_gold and any(w in q for w in ["silver", "chandi"])
        need_idx = any(w in q for w in idx_kw)
        need_fx = any(w in q for w in fx_kw)
        need_oil = any(w in q for w in oil_kw)
        need_rates = any(w in q for w in rate_kw)

        # Fire all independent yfinance calls in parallel
        futures = {}
        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="mktdata") as pool:
            if need_gold:
                futures[pool.submit(get_gold_silver_price)] = "gold"
            if need_idx:
                futures[pool.submit(get_stock_price, "^NSEI")] = "nifty"
                futures[pool.submit(get_stock_price, "^BSESN")] = "sensex"
            if need_fx:
                futures[pool.submit(get_forex_rate, "USD", "INR")] = "usdinr"
            if need_oil:
                futures[pool.submit(get_stock_price, "CL=F")] = "crude"
            if need_rates:
                from tools.web_search import web_search
                futures[pool.submit(web_search, "India RBI repo rate FD rate PPF rate latest 2026", 3)] = "rates"

        results = {}
        for future in as_completed(futures):
            tag = futures[future]
            try:
                results[tag] = future.result()
            except Exception:
                pass

        # Format results
        if "gold" in results:
            data = results["gold"]
            if data.get("gold_usd") and data.get("usd_inr_rate"):
                usd_inr = data["usd_inr_rate"]
                gold_inr_10g = round(data["gold_usd"] * usd_inr / 31.1035 * 10, 0)
                gold_inr_1g = round(gold_inr_10g / 10, 0)
                parts.append(
                    f"LIVE GOLD PRICE: ₹{gold_inr_10g:,.0f}/10g (24K) | "
                    f"₹{gold_inr_1g:,.0f}/g | ${data['gold_usd']:,.2f}/troy oz | "
                    f"USD/INR: {usd_inr}"
                )
            if need_silver and data.get("silver_usd") and data.get("usd_inr_rate"):
                silver_inr_kg = round(data["silver_usd"] * data["usd_inr_rate"] / 31.1035 * 1000, 0)
                parts.append(
                    f"LIVE SILVER PRICE: ₹{silver_inr_kg:,.0f}/kg | "
                    f"${data['silver_usd']:,.2f}/troy oz"
                )

        if "nifty" in results:
            nifty = results["nifty"]
            if "error" not in nifty:
                parts.append(f"LIVE NIFTY 50: {nifty['price']:,.2f} ({nifty['change_pct']:+.2f}%)")
        if "sensex" in results:
            sensex = results["sensex"]
            if "error" not in sensex:
                parts.append(f"LIVE SENSEX: {sensex['price']:,.2f} ({sensex['change_pct']:+.2f}%)")

        if "usdinr" in results:
            usdinr = results["usdinr"]
            if "error" not in usdinr:
                parts.append(f"LIVE USD/INR: ₹{usdinr['rate']}")

        if "rates" in results:
            rate_data = results["rates"]
            if rate_data and "error" not in rate_data[0]:
                parts.append("LATEST RATE DATA:")
                for r in rate_data[:2]:
                    parts.append(f"  • {r.get('title', '')}: {r.get('snippet', '')}")

        if "crude" in results:
            crude = results["crude"]
            if "error" not in crude:
                parts.append(
                    f"LIVE CRUDE OIL (WTI): ${crude['price']:,.2f}/barrel "
                    f"({crude['change_pct']:+.2f}%)"
                )

        if parts:
            logger.info(f"[{self.name}] Auto-fetched live market data: {len(parts)} items")

        return "\n".join(parts) if parts else ""

    def gather_context(self, query: str) -> str:
        """Override in subclasses to gather tool data before LLM call."""
        return ""

    def process(self, query: str) -> str:
        """Process a user query through this agent."""
        logger.info(f"{'='*60}")
        logger.info(f"[{self.name}] Processing query: {query[:100]}")

        # Step 1: Gather context
        t0 = time.time()
        try:
            context = self.gather_context(query)
            logger.info(f"[{self.name}] Context gathered in {time.time()-t0:.1f}s | len={len(context)}")
        except Exception as e:
            logger.error(f"[{self.name}] gather_context FAILED: {e}\n{traceback.format_exc()}")
            context = ""

        # Step 2: Generate response
        t1 = time.time()
        try:
            response = llm.generate(self.system_prompt, query, context)
            logger.info(f"[{self.name}] LLM response in {time.time()-t1:.1f}s | total={time.time()-t0:.1f}s | response_len={len(response)}")
        except Exception as e:
            logger.error(f"[{self.name}] LLM generate FAILED: {e}\n{traceback.format_exc()}")
            raise

        if not response or not response.strip():
            logger.error(f"[{self.name}] LLM returned EMPTY response!")
            return "I apologize, but I couldn't generate a response. Please try rephrasing your question."

        return response
