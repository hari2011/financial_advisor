"""Mutual Fund Advisor Agent - India specific."""
import json
from agents.base import BaseAgent, fmt_inr
from tools.web_search import web_search
from tools.financial_calc import sip_calculator, compound_interest, inflation_adjusted_return, ctc_to_take_home


class MutualFundAdvisorAgent(BaseAgent):
    name = "Mutual Fund Advisor"
    icon = "📊"
    description = "Indian mutual fund selection, SIP planning, ELSS, fund comparison, AMC analysis"

    system_prompt = """SEBI-registered AMFI-certified MF advisor for Indian investors. Explain fund choices clearly — users need to understand why a specific fund fits their goal.

APPROACH: Profile investor → Goal → Category → Specific funds (max 4-6, no overlap) → SIP → Tax implications.
- ELSS: 3yr lock-in, check 80C space after EPF. Index: Nifty50 + Next50 = core passive.
- Active large cap rarely beats index. Active mid/small can outperform but volatile.
- Direct saves 0.5-1.5% = ₹5-15L+ over 20yr on ₹10K SIP. LTCG harvest ₹1.25L/yr.
- New investor: 1 index + 1 flexi cap. Too many funds(>8): consolidate.
- Step-up SIP +10%/yr compounds dramatically. SIP in volatile, lumpsum in clear bull.
- AMCs: SBI, HDFC, ICICI Pru, Mirae, PPFAS, Motilal. Platforms: Kuvera, Groww, Coin.

FORMAT: Use PRE-COMPUTED data. DIRECT plans only. Fund comparison tables with category + rationale. End with: (1) recommended funds with why each was chosen (2) SIP amount (3) when to review."""

    def gather_context(self, query: str) -> str:
        context_parts = []
        # ── Inject relevant financial knowledge ──
        knowledge = self.get_knowledge_context(query)
        if knowledge:
            context_parts.append(knowledge)
        query_lower = query.lower()
        numbers = self.extract_numbers(query)

        # ── Pre-compute SIP projections if user mentions amounts ──
        if numbers:
            num_labels = [fmt_inr(n) for n in numbers]
            context_parts.append(f"EXTRACTED AMOUNTS: {', '.join(num_labels)}")

            sip_amounts = [n for n in numbers if 500 <= n <= 500000]
            lumpsum_amounts = [n for n in numbers if n >= 10000]

            # Check if the number is income/CTC rather than SIP amount
            freq = self.detect_income_frequency(query)
            is_income = any(w in query_lower for w in ["ctc", "salary", "income", "earn",
                                                        "package", "lpa", "per annum"])

            if (is_income or freq == "annual") and numbers[0] >= 100000:
                th = ctc_to_take_home(numbers[0])
                take_home = th['take_home_monthly_new']
                suggested_sip = round(take_home * 0.20 / 1000) * 1000
                context_parts.append(
                    f"\nINCOME ANALYSIS:\n"
                    f"  CTC: {fmt_inr(th['ctc_annual'])}/yr\n"
                    f"  Take-home: {fmt_inr(take_home)}/mo (new regime)\n"
                    f"  Suggested SIP (20% of take-home): {fmt_inr(suggested_sip)}/mo"
                )
                if not sip_amounts:
                    sip_amounts = [suggested_sip]

            # SIP projections for user's exact amount
            if sip_amounts or any(w in query_lower for w in ["sip", "monthly", "per month"]):
                monthly = sip_amounts[0] if sip_amounts else 10000
                context_parts.append(f"\nSIP PROJECTIONS for {fmt_inr(monthly)}/month:")
                for rate in [10, 12]:
                    for years in [5, 10, 20, 30]:
                        s = sip_calculator(monthly, rate, years)
                        context_parts.append(
                            f"  @{rate}% for {years}yr: Invested {fmt_inr(s['total_invested'])} → "
                            f"Value {fmt_inr(s['future_value'])}"
                        )

            # Lumpsum projections
            if lumpsum_amounts and any(w in query_lower for w in ["lumpsum", "lump sum", "one time", "invest"]):
                principal = lumpsum_amounts[0]
                context_parts.append(f"\nLUMPSUM PROJECTIONS for {fmt_inr(principal)}:")
                for rate in [10, 12]:
                    for years in [5, 10, 20]:
                        c = compound_interest(principal, rate, years)
                        context_parts.append(
                            f"  @{rate}% for {years}yr → {fmt_inr(c['final_amount'])}"
                        )

        # ── Default SIP reference if no numbers given ──
        if not numbers:
            context_parts.append("SIP REFERENCE (@12% return):")
            for amt in [5000, 10000, 25000]:
                for years in [10, 20, 30]:
                    s = sip_calculator(amt, 12, years)
                    context_parts.append(
                        f"  {fmt_inr(amt)}/mo × {years}yr → {fmt_inr(s['future_value'])}"
                    )

        # ── ELSS tax saving calculation ──
        if any(w in query_lower for w in ["elss", "80c", "tax saving", "tax saver"]):
            # Max 80C via ELSS = ₹1.5L/yr = ₹12,500/mo
            s = sip_calculator(12500, 12, 3)  # 3yr lock-in
            context_parts.append(
                f"\nELSS TAX MATH:\n"
                f"  Max 80C SIP: ₹12,500/mo (₹1.5L/yr)\n"
                f"  After 3yr lock-in @12%: {fmt_inr(s['future_value'])}\n"
                f"  Tax saved (30% bracket): ₹45,000/yr"
            )

        # ── Web search derived from user query ──
        fund_type_map = {
            ("elss", "tax saving", "80c"): "ELSS tax saving",
            ("index", "nifty", "passive"): "index fund Nifty 50",
            ("small cap",): "small cap",
            ("mid cap",): "mid cap",
            ("large cap",): "large cap",
            ("flexi", "multi cap"): "flexi cap multi cap",
            ("debt", "liquid", "short duration"): "debt liquid",
            ("hybrid", "balanced"): "hybrid balanced advantage",
        }
        fund_category = "mutual fund"
        for keywords, cat in fund_type_map.items():
            if any(k in query_lower for k in keywords):
                fund_category = cat
                break
        search_q = f"best {fund_category} funds India 2025 2026 direct plan"

        web_data = web_search(search_q, max_results=3)
        if web_data and "error" not in web_data[0]:
            context_parts.append("MUTUAL FUND DATA:")
            for r in web_data[:3]:
                context_parts.append(f"  • {r.get('title', '')}: {r.get('snippet', '')}")

        # Nifty 50 level — summarized, not JSON
        from tools.market_data import get_stock_price
        nifty = get_stock_price("^NSEI")
        if "error" not in nifty:
            price = nifty.get("current_price") or nifty.get("price", 0)
            change = nifty.get("change_pct", 0)
            context_parts.append(f"NIFTY 50: ₹{price:,.2f} ({change:+.2f}%)")

        live_data = self._auto_market_data(query)
        if live_data:
            context_parts.append(f"LIVE MARKET DATA:\n{live_data}")

        return "\n\n".join(context_parts)
