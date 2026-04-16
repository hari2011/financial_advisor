"""Portfolio Manager Agent - India focused."""
import json
from agents.base import BaseAgent, fmt_inr
from tools.market_data import get_stock_price, get_multiple_stocks
from tools.financial_calc import portfolio_return, cagr, ctc_to_take_home, sip_calculator, compound_interest


class PortfolioManagerAgent(BaseAgent):
    name = "Portfolio Manager"
    icon = "💼"
    description = "Portfolio construction, asset allocation, Indian mutual funds, diversification, rebalancing"

    system_prompt = """SEBI-registered Portfolio Manager for Indian investors. Explain allocation logic so the user understands why each choice fits their profile.

APPROACH: Profile investor (age, risk, goals) → Assess current allocation → Identify gaps → Design target → Tax-optimize.
- EPF(8.15%)+PPF(7.1%) = debt allocation. Don’t over-add debt MF.
- Assets: Equity (index+active), Debt (PPF/EPF/debt MF), Gold (SGB), International (Nasdaq/S&P).
- Aggressive(22-28): 80% equity/15% debt/5% gold. Moderate(30-40): 60/25/10/5. Conservative(50+): 30/50/15/5.
- Rebalance annually if any class drifts >5%. Tax-harvest ₹1.25L LTCG/yr.
- FD at 30% bracket = 4.9% post-tax, minus 6% inflation = negative real return.

FORMAT: Use PRE-COMPUTED data. Name specific funds/instruments. Explain why each fits. Tables for allocation. End with: (1) target allocation with reasoning (2) specific instruments (3) rebalance plan."""

    def gather_context(self, query: str) -> str:
        context_parts = []
        # ── Inject relevant financial knowledge ──
        knowledge = self.get_knowledge_context(query)
        if knowledge:
            context_parts.append(knowledge)
        tickers = self.extract_tickers(query)
        numbers = self.extract_numbers(query)
        query_lower = query.lower()

        # If income/CTC mentioned, compute tax and investable surplus
        if numbers:
            raw_income = numbers[0]
            freq = self.detect_income_frequency(query)
            is_ctc = any(w in query_lower for w in ["ctc", "package", "lpa", "per year",
                                                     "per annum", "/year", "annual", "salary"])
            if (freq == "annual" or is_ctc) and raw_income >= 100000:
                th = ctc_to_take_home(raw_income)
                take_home_monthly = th['take_home_monthly_new']
                context_parts.append(
                    f"INCOME & TAX ANALYSIS:\n"
                    f"  CTC: {fmt_inr(th['ctc_annual'])} /year | Basic ({th['basic_pct']}%): {fmt_inr(th['basic'])}\n"
                    f"  EPF (employee): {fmt_inr(th['epf_employee'])} /year (counts as debt allocation)\n"
                    f"  EPF (employer): {fmt_inr(th['epf_employer_total'])} /year → retirement corpus\n"
                    f"  Gratuity provision: {fmt_inr(th['gratuity_annual_provision'])} /year\n"
                    f"  Tax (New Regime): {fmt_inr(th['tax_new_regime'])} ({th['effective_tax_rate_new']}%)\n"
                    f"  Tax (Old Regime): {fmt_inr(th['tax_old_regime'])} ({th['effective_tax_rate_old']}%)\n"
                    f"  Take-home: {fmt_inr(th['take_home_monthly_new'])} /month (new) | "
                    f"{fmt_inr(th['take_home_monthly_old'])} /month (old)\n"
                    f"  Total retirement accrual: {fmt_inr(th['total_retirement_annual'])} /year"
                )

                # Pre-compute investable amounts at different savings rates
                for savings_pct in [20, 30, 40]:
                    investable = round(take_home_monthly * savings_pct / 100)
                    context_parts.append(
                        f"  {savings_pct}% savings rate → {fmt_inr(investable)}/month investable"
                    )

                # SIP projections for likely SIP amounts
                likely_sip = round(take_home_monthly * 0.2 / 1000) * 1000  # 20% rounded
                for years in [10, 20, 30]:
                    s = sip_calculator(likely_sip, 12, years)
                    context_parts.append(
                        f"SIP {fmt_inr(likely_sip)}/mo (20% savings) @12% → "
                        f"{years}yr: {fmt_inr(s['future_value'])}"
                    )

            # Pass all extracted numbers
            num_labels = [fmt_inr(n) for n in numbers]
            context_parts.append(f"EXTRACTED AMOUNTS: {', '.join(num_labels)}")

            # Lumpsum projection if user has a lump amount
            lump_amounts = [n for n in numbers if n >= 100000]
            if lump_amounts:
                principal = lump_amounts[0]
                context_parts.append(f"\nLUMPSUM PROJECTIONS for {fmt_inr(principal)}:")
                for rate in [8, 10, 12]:
                    for years in [5, 10, 20]:
                        c = compound_interest(principal, rate, years)
                        context_parts.append(
                            f"  @{rate}% for {years}yr → {fmt_inr(c['final_amount'])}"
                        )

        # Pre-compute model portfolio returns
        model_portfolios = {
            "Conservative (30E/50D/10G/10C)": [
                (30, 12), (50, 7), (10, 9), (10, 5)
            ],
            "Moderate (50E/30D/10G/10A)": [
                (50, 12), (30, 7), (10, 9), (10, 8)
            ],
            "Aggressive (75E/15D/5G/5I)": [
                (75, 12), (15, 7), (5, 9), (5, 10)
            ],
        }
        context_parts.append("\nMODEL PORTFOLIO EXPECTED RETURNS:")
        for name, holdings in model_portfolios.items():
            ret = portfolio_return(holdings)
            context_parts.append(f"  {name}: {ret['portfolio_return']:.1f}% p.a.")

        if tickers:
            stocks = get_multiple_stocks(tickers)
            # Summarize holdings instead of JSON dump
            if isinstance(stocks, dict):
                for sym, data in stocks.items():
                    if isinstance(data, dict) and "error" not in data:
                        price = data.get("current_price") or data.get("price", 0)
                        change = data.get("change_pct", 0)
                        context_parts.append(f"  {sym}: ₹{price:,.2f} ({change:+.2f}%)")

        # Indian benchmarks — summarized, not JSON
        benchmarks = get_multiple_stocks(["^NSEI", "^BSESN"])
        if isinstance(benchmarks, dict):
            bench_lines = ["BENCHMARKS:"]
            for sym, data in benchmarks.items():
                if isinstance(data, dict) and "error" not in data:
                    price = data.get("current_price") or data.get("price", 0)
                    change = data.get("change_pct", 0)
                    name = data.get("name", sym)
                    bench_lines.append(f"  {name}: ₹{price:,.2f} ({change:+.2f}%)")
            context_parts.append("\n".join(bench_lines))

        # Web search derived from actual user query
        if not tickers and not numbers:
            web_data = self.web_lookup(f"{self.extract_search_keywords(query)} portfolio allocation India")
            if web_data:
                context_parts.append(f"LATEST DATA:\n{web_data}")

        return "\n\n".join(context_parts)
