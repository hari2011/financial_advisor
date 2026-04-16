"""Budget & Savings Planner Agent."""
from agents.base import BaseAgent, fmt_inr
from tools.financial_calc import sip_calculator, ctc_to_take_home, emergency_fund


class BudgetPlannerAgent(BaseAgent):
    name = "Budget & Savings Planner"
    icon = "💰"
    description = "Budgeting in ₹, expense tracking, savings goals, emergency fund, financial health"

    system_prompt = """Certified Financial Planner for Indian households. Give specific ₹ amounts — not just percentages — so the user has a ready-to-use budget.

APPROACH: Take-home(not CTC) → Life stage → Fixed commitments → Choose framework → Specific ₹ budget.
- Frameworks: 50/30/20 (balanced), 60/20/20 (high-cost city), 40/20/40 (aggressive saver), 70/10/20 (low income).
- Emergency fund = 6mo expenses. EPF already saves ~12% Basic for retirement. Insurance is non-negotiable.
- Step-up SIP +10%/yr with hikes. Even ₹5K/mo = ₹1Cr+ in 25yr @12%.
- Budget from TAKE-HOME only. Debt stress → payoff first.

FORMAT: Use PRE-COMPUTED data. Budget table with specific ₹ amounts per category. Explain why each allocation matters. End with: (1) recommended framework for their situation (2) monthly budget breakdown (3) one quick win they can start today."""

    def gather_context(self, query: str) -> str:
        context_parts = []

        # ── Inject relevant financial knowledge ──
        knowledge = self.get_knowledge_context(query)
        if knowledge:
            context_parts.append(knowledge)

        numbers = self.extract_numbers(query)
        query_lower = query.lower()

        if numbers:
            raw_income = numbers[0]
            freq = self.detect_income_frequency(query)

            # CTC/annual income → compute take-home with tax (deterministic math)
            is_ctc = any(w in query_lower for w in ["ctc", "package", "lpa", "per year",
                                                     "per annum", "/year", "annual"])
            if freq == "annual" or is_ctc:
                annual_ctc = raw_income
                th = ctc_to_take_home(annual_ctc)
                context_parts.append(
                    f"SALARY BREAKDOWN (CTC → Take-Home):\n"
                    f"  CTC (Annual): {fmt_inr(th['ctc_annual'])}\n"
                    f"  Basic ({th['basic_pct']}%): {fmt_inr(th['basic'])} ({fmt_inr(th['basic_monthly'])}/mo)\n"
                    f"  HRA (50% of Basic): {fmt_inr(th['hra'])}\n"
                    f"  EPF Employee (12% of Basic): {fmt_inr(th['epf_employee'])}/yr\n"
                    f"  EPF Employer (12% of Basic): {fmt_inr(th['epf_employer_total'])}/yr\n"
                    f"  Gratuity provision: {fmt_inr(th['gratuity_annual_provision'])}/yr\n"
                    f"  Income Tax (New): {fmt_inr(th['tax_new_regime'])} ({th['effective_tax_rate_new']}%)\n"
                    f"  Income Tax (Old): {fmt_inr(th['tax_old_regime'])} ({th['effective_tax_rate_old']}%)\n"
                    f"  ---\n"
                    f"  TAKE-HOME (New): {fmt_inr(th['take_home_monthly_new'])}/mo = {fmt_inr(th['take_home_annual_new'])}/yr\n"
                    f"  TAKE-HOME (Old): {fmt_inr(th['take_home_monthly_old'])}/mo = {fmt_inr(th['take_home_annual_old'])}/yr\n"
                    f"  Retirement accrual (EPF+Gratuity): {fmt_inr(th['total_retirement_annual'])}/yr"
                )
                income = th['take_home_monthly_new']
            else:
                income = raw_income
                context_parts.append(f"INPUT: Monthly income = {fmt_inr(income)}")

            # Detect EMIs from query
            emi_amounts = []
            if any(w in query_lower for w in ["emi", "loan", "repayment"]) and len(numbers) > 1:
                emi_amounts = [n for n in numbers[1:] if 1000 <= n <= income * 0.6]

            total_emi = sum(emi_amounts)
            if total_emi > 0:
                disposable = round(income - total_emi)
                context_parts.append(
                    f"\nPRE-DEDUCTIONS:\n"
                    f"  Take-home: {fmt_inr(income)}/mo\n"
                    f"  EMI/Obligations: {fmt_inr(total_emi)}/mo\n"
                    f"  Disposable (after EMI): {fmt_inr(disposable)}/mo"
                )
            else:
                disposable = income
                context_parts.append(f"\nDISPOSABLE INCOME: {fmt_inr(disposable)}/mo")

            # Emergency fund target (6 months of estimated expenses)
            est_expenses = round(disposable * 0.55)
            ef = emergency_fund(est_expenses, 6)
            context_parts.append(
                f"\nEMERGENCY FUND TARGET: {fmt_inr(ef['emergency_fund_amount'])} "
                f"(estimated {fmt_inr(est_expenses)}/mo expenses × 6 months)"
            )

            # SIP projections for reference at different saving rates
            for save_pct in [15, 20, 30]:
                sip_amount = round(disposable * save_pct / 100)
                sip_20yr = sip_calculator(sip_amount, 12, 20)
                context_parts.append(
                    f"SIP: {fmt_inr(sip_amount)}/mo ({save_pct}% of disposable) @12% for 20yr → "
                    f"{fmt_inr(sip_20yr['future_value'])}"
                )

        if not context_parts:
            context_parts.append("No income data found in query. Ask user for monthly income or CTC.")

        live_data = self._auto_market_data(query)
        if live_data:
            context_parts.append(f"LIVE MARKET DATA:\n{live_data}")

        return "\n\n".join(context_parts)
