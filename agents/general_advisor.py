"""General Financial Advisor Agent - catch-all for general queries."""
import json
from agents.base import BaseAgent, fmt_inr
from tools.web_search import web_search, financial_news
from tools.financial_calc import (
    sip_calculator, emi_calculator, compound_interest,
    emergency_fund, savings_rate, debt_to_income,
    ctc_to_take_home, rule_of_72,
)


class GeneralAdvisorAgent(BaseAgent):
    name = "General Financial Advisor"
    icon = "🧠"
    description = "General financial advice, concepts, education, news, and catch-all queries"

    system_prompt = """Financial Advisor for Indian personal finance. Explain financial concepts simply — the user needs to understand the ‘why’ behind your advice.

APPROACH: Understand situation → Core question → Consider interdependencies → Specific actions.
- Priority order: Emergency fund → Health insurance → Term life → Debt payoff → Investment.
- Returns: Equity ~12%, Debt 7%, Gold 8-10%, Real estate 5-8%, Inflation ~6%.
- Real return = Nominal − Inflation − Tax. 7% FD @30% = 4.9% post-tax − 6% inflation = -1.1% real.
- ₹10K/mo × 30yr @12% = ₹3.53Cr. 5yr late = ₹1.76Cr (50% less). EPF+PPF = best risk-free EEE.
- Overwhelmed → simplify to 3 actions. A vs B → pros/cons table + recommendation.
- Govt schemes: PPF(7.1%,EEE), SSY(8.2%,girl child), NPS(80CCD(1B)₹50K), SCSS(8.2%,60+), NSC(7.7%), KVP, POMIS(7.4%), APY.
- NRI banking: NRE(tax-free, repatriable), NRO(Indian income, 30%TDS), FCNR(forex-safe). FEMA rules for NRI investments.

FORMAT: Use PRE-COMPUTED data. ₹ Lakhs/Crores. Bullets and tables for data points. Explain reasoning. End with: (1) direct answer to the question (2) 2-3 specific next steps (3) one insight they shouldn’t miss."""

    def gather_context(self, query: str) -> str:
        context_parts = []
        # ── Inject relevant financial knowledge ──
        knowledge = self.get_knowledge_context(query)
        if knowledge:
            context_parts.append(knowledge)
        query_lower = query.lower()
        numbers = self.extract_numbers(query)

        # ── Pre-compute calculations for any detected numbers ──
        if numbers:
            num_labels = [fmt_inr(n) for n in numbers]
            context_parts.append(f"EXTRACTED AMOUNTS: {', '.join(num_labels)}")

            amounts = [n for n in numbers if n >= 500]

            # Determine if the primary number is income/CTC or an investment amount
            freq = self.detect_income_frequency(query)
            is_income = any(w in query_lower for w in ["ctc", "salary", "income", "earn",
                                                        "package", "lpa", "per annum"])
            take_home_monthly = None
            if (is_income or freq == "annual") and amounts and amounts[0] >= 100000:
                th = ctc_to_take_home(amounts[0])
                take_home_monthly = th['take_home_monthly_new']
                context_parts.append(
                    f"\nSALARY BREAKDOWN:\n"
                    f"  CTC: {fmt_inr(th['ctc_annual'])}/yr\n"
                    f"  Take-home (New): {fmt_inr(th['take_home_monthly_new'])}/mo\n"
                    f"  Take-home (Old): {fmt_inr(th['take_home_monthly_old'])}/mo\n"
                    f"  Tax New: {fmt_inr(th['tax_new_regime'])} ({th['effective_tax_rate_new']}%)\n"
                    f"  Tax Old: {fmt_inr(th['tax_old_regime'])} ({th['effective_tax_rate_old']}%)"
                )

            # SIP projections if SIP/invest/monthly mentioned
            if any(w in query_lower for w in ["sip", "invest", "monthly", "per month", "mutual fund"]):
                # If user gave income, suggest SIP at 20% of take-home; otherwise use extracted amount
                sip_amounts = [n for n in numbers if 500 <= n <= 500000]
                if sip_amounts:
                    monthly = sip_amounts[0]
                elif take_home_monthly:
                    monthly = round(take_home_monthly * 0.20 / 1000) * 1000  # 20% rounded
                    context_parts.append(f"  Suggested SIP (20% of take-home): {fmt_inr(monthly)}/mo")
                else:
                    monthly = 10000
                context_parts.append(f"\nSIP PROJECTIONS for {fmt_inr(monthly)}/month:")
                for rate in [10, 12]:
                    for years in [5, 10, 20, 30]:
                        s = sip_calculator(monthly, rate, years)
                        context_parts.append(
                            f"  @{rate}% for {years}yr: Invested {fmt_inr(s['total_invested'])} → "
                            f"Value {fmt_inr(s['future_value'])}"
                        )

            # EMI if loan/emi/borrow mentioned
            if any(w in query_lower for w in ["emi", "loan", "borrow", "home loan"]):
                principal = max(amounts) if amounts else 5000000
                context_parts.append(f"\nEMI TABLE for {fmt_inr(principal)}:")
                for rate in [8.5, 9.0, 9.5]:
                    for tenure in [15, 20, 30]:
                        e = emi_calculator(principal, rate, tenure * 12)
                        context_parts.append(
                            f"  {rate}% × {tenure}yr: EMI {fmt_inr(e['emi'])} | "
                            f"Interest {fmt_inr(e['total_interest'])}"
                        )

            # Lumpsum growth if invest/grow/compound mentioned
            if any(w in query_lower for w in ["lumpsum", "lump sum", "grow", "compound", "fd", "fixed deposit"]):
                principal = amounts[0] if amounts else 100000
                context_parts.append(f"\nGROWTH PROJECTIONS for {fmt_inr(principal)}:")
                for rate in [7, 10, 12]:
                    for years in [3, 5, 10]:
                        c = compound_interest(principal, rate, years)
                        context_parts.append(
                            f"  @{rate}% for {years}yr → {fmt_inr(c['final_amount'])}"
                        )

            # Emergency fund
            if any(w in query_lower for w in ["emergency", "rainy day", "buffer"]):
                monthly_exp = amounts[0] if amounts else 50000
                ef = emergency_fund(monthly_exp, 6)
                context_parts.append(
                    f"\nEMERGENCY FUND: {fmt_inr(monthly_exp)}/mo expenses × 6 months = "
                    f"{fmt_inr(ef['emergency_fund_amount'])}"
                )


            # Doubling time
            if any(w in query_lower for w in ["double", "doubling", "rule of 72"]):
                for rate in [7, 8, 10, 12, 14, 15]:
                    r72 = rule_of_72(rate)
                    context_parts.append(f"Rule of 72: @{rate}% → doubles in {r72['years_to_double']:.1f} years")

        # Get financial news only if the query is about news/market/economy
        if any(w in query_lower for w in ["news", "market", "economy", "latest", "today", "update"]):
            news = financial_news()
            if news and "error" not in news[0]:
                context_parts.append("TODAY'S FINANCIAL NEWS:")
                for n in news[:3]:
                    context_parts.append(f"  • [{n.get('source', '')}] {n.get('title', '')}: {n.get('snippet', '')}")

        # Targeted web search derived from user query
        topic_searches = {
            ("gold", "gold rate", "gold price", "sona"): "gold rate price India today",
            ("silver", "silver rate", "chandi"): "silver rate price India today",
            ("dollar", "usd", "forex", "exchange rate"): "USD INR dollar rate today",
            ("crude", "oil price", "petrol", "diesel"): "crude oil price India today",
            ("ppf", "epf", "provident"): "PPF EPF interest rate",
            ("fd", "fixed deposit"): "fixed deposit FD rates India",
            ("nps", "pension"): "NPS returns tier 1",
            ("sgb", "sovereign"): "sovereign gold bond SGB India",
            ("budget", "union budget"): "India union budget highlights",
            ("rbi", "repo", "monetary"): "RBI repo rate monetary policy",
            ("inflation", "cpi"): "India CPI inflation rate",
            ("elss", "80c", "tax saving"): "ELSS tax saving mutual funds",
        }
        for keywords, topic in topic_searches.items():
            if any(k in query_lower for k in keywords):
                search_q = f"{self.extract_search_keywords(query)} {topic} India 2025 2026"
                web_data = self.web_lookup(search_q)
                if web_data:
                    context_parts.append(f"LATEST DATA:\n{web_data}")
                break

        # Fetch live market data if query mentions gold, rates, market, etc.
        live_data = self._auto_market_data(query)
        if live_data:
            context_parts.append(f"LIVE MARKET DATA:\n{live_data}")

        return "\n\n".join(context_parts)
