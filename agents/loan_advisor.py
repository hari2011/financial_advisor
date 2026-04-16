"""Loan & Mortgage Advisor Agent."""
import json
from agents.base import BaseAgent, fmt_inr
from tools.financial_calc import emi_calculator, loan_amortization, ctc_to_take_home


class LoanAdvisorAgent(BaseAgent):
    name = "Loan & EMI Advisor"
    icon = "🏠"
    description = "Home loan EMI, personal loans, gold loans, PMAY, RBI rates, debt management"

    system_prompt = """Loan & EMI Specialist for Indian market. Help users understand the true cost of borrowing and smart repayment strategies.

APPROACH: Understand need → Affordability(EMI ≤40% take-home) → Compare options → Tax benefits → Prepayment strategy.
- Prepayment in early years saves massive interest. Joint home loan doubles tax benefits (each claims 24b+80C).
- Effective cost with tax: 8.5% home loan → ~5.9% for 30% bracket. Balance transfer if rate >0.5% above market.
- Loan vs Invest: If rate < expected return (8.5% vs 12%), investing may beat prepayment.
- Rates 2025-26: Home 8.25-9.5% float. Personal 10.5-24%. Education 8-14% (80E). Car 8-12%. Gold 7-12%.
- CIBIL 750+ for best rates. FOIR cap 50-60%.

FORMAT: Use PRE-COMPUTED data. EMI comparison tables showing total interest paid. Explain trade-offs clearly. End with: (1) recommended loan structure (2) prepayment strategy with savings shown (3) one important caution."""

    def gather_context(self, query: str) -> str:
        context_parts = []

        # ── Inject relevant financial knowledge ──
        knowledge = self.get_knowledge_context(query)
        if knowledge:
            context_parts.append(knowledge)

        numbers = self.extract_numbers(query)
        query_lower = query.lower()

        if numbers:
            # Pass all extracted numbers for LLM reference
            num_labels = [fmt_inr(n) for n in numbers]
            context_parts.append(f"EXTRACTED AMOUNTS: {', '.join(num_labels)}")

            freq = self.detect_income_frequency(query)
            is_income = any(w in query_lower for w in ["ctc", "salary", "income", "earn",
                                                        "package", "lpa", "afford"])

            # Separate income from loan amount
            large_nums = sorted([n for n in numbers if n >= 10000], reverse=True)
            take_home_monthly = None

            if is_income or freq == "annual":
                # First number is likely income, use it for affordability
                income_num = numbers[0]
                if income_num >= 100000 and (freq == "annual" or income_num >= 500000):
                    th = ctc_to_take_home(income_num)
                    take_home_monthly = th['take_home_monthly_new']
                    context_parts.append(
                        f"\nINCOME ANALYSIS:\n"
                        f"  CTC: {fmt_inr(th['ctc_annual'])}/yr\n"
                        f"  Take-home: {fmt_inr(take_home_monthly)}/mo (new regime)\n"
                    )
                    # Affordability: max EMI at 40% and 50% of take-home
                    max_emi_40 = round(take_home_monthly * 0.40)
                    max_emi_50 = round(take_home_monthly * 0.50)
                    context_parts.append(
                        f"AFFORDABILITY:\n"
                        f"  Max EMI (40% of take-home, safe): {fmt_inr(max_emi_40)}/mo\n"
                        f"  Max EMI (50% of take-home, stretched): {fmt_inr(max_emi_50)}/mo"
                    )
                    # Compute max loan at different rates for 40% EMI
                    context_parts.append(f"\nMAX LOAN AFFORDABLE (EMI ≤ {fmt_inr(max_emi_40)}/mo):")
                    for rate in [8.5, 9.0, 9.5]:
                        for tenure in [20, 30]:
                            r = rate / 100 / 12
                            n_months = tenure * 12
                            max_loan = max_emi_40 * ((1 + r) ** n_months - 1) / (r * (1 + r) ** n_months)
                            context_parts.append(
                                f"  {rate}% × {tenure}yr → Max loan: {fmt_inr(round(max_loan))}"
                            )
                    # Remove income from loan principal candidates
                    large_nums = [n for n in large_nums if n != income_num]

            # Find loan principal (largest remaining number, or use the only number if not income)
            principal = large_nums[0] if large_nums else (numbers[0] if not take_home_monthly else None)

            if principal and principal >= 10000:
                # Generate EMI tables
                context_parts.append(f"\nEMI TABLE for {fmt_inr(principal)}:")
                for rate in [8.5, 9.0, 9.5]:
                    for tenure_years in [15, 20, 30]:
                        emi_data = emi_calculator(principal, rate, tenure_years * 12)
                        emi_line = (
                            f"  {rate}% × {tenure_years}yr: EMI {fmt_inr(emi_data['emi'])} | "
                            f"Interest {fmt_inr(emi_data['total_interest'])} | "
                            f"Total {fmt_inr(emi_data['total_payment'])}"
                        )
                        # Flag if EMI exceeds affordability
                        if take_home_monthly and emi_data['emi'] > take_home_monthly * 0.50:
                            emi_line += " ⚠️ EXCEEDS 50% take-home"
                        elif take_home_monthly and emi_data['emi'] > take_home_monthly * 0.40:
                            emi_line += " ⚠️ STRETCHED (>40% take-home)"
                        context_parts.append(emi_line)

        if not context_parts:
            context_parts.append("No loan amount found. Ask user for loan principal, rate, and tenure.")

        # Fetch live market data (repo rate, gold rate for gold loans, etc.)
        live_data = self._auto_market_data(query)
        if live_data:
            context_parts.append(f"LIVE MARKET DATA:\n{live_data}")

        # Fetch latest loan interest rates
        from tools.web_search import web_search as ws
        loan_type = "home loan"
        for lt in ["car loan", "personal loan", "education loan", "gold loan", "LAP"]:
            if lt in query_lower:
                loan_type = lt
                break
        search_q = f"{loan_type} interest rates India 2025 2026"
        rate_info = ws(search_q, max_results=3)
        if rate_info and "error" not in rate_info[0]:
            context_parts.append(f"LATEST {loan_type.upper()} RATES:")
            for r in rate_info[:2]:
                context_parts.append(f"  • {r.get('title', '')}: {r.get('snippet', '')}")

        return "\n\n".join(context_parts)
