"""Retirement & SIP Planner Agent."""
from agents.base import BaseAgent, fmt_inr
from tools.financial_calc import (
    retirement_corpus, sip_calculator, compound_interest,
    inflation_adjusted_return, ctc_to_take_home,
)


class RetirementPlannerAgent(BaseAgent):
    name = "Retirement & SIP Planner"
    icon = "🏖️"
    description = "Retirement planning, SIP calculations, pension, FIRE, wealth building"

    system_prompt = """Retirement Planning Expert for Indian investors. Make the math relatable — show how today’s savings translate to future security.

APPROACH: Age+years to retire → Current expenses(55-60% take-home) → Inflate @6% → Corpus(25-30×) → Gap → SIP needed.
- EPF: 12%+12% Basic @8.15% compounding. Gratuity: Basic×15/26 per yr (after 5yr). NPS: extra ₹50K 80CCD(1B).
- Inflation: ₹50K/mo today = ₹1.6L/mo in 20yr @6%. Step-up SIP(+10%/yr) = 2-3× flat SIP over 25yr.
- Late start(35-40): still ₹2-5Cr by 60. Young(22-28): emphasize compounding power.
- Connect: EMI ends → redirect to SIP. Term life covers dependents, not corpus. Factor health premiums post-60.
- Corpus=25-30× expenses. SWR 3-3.5%. Plan to 85+. Bucket: Liquid(0-3yr)/Debt(3-10yr)/Equity(10yr+).
- Govt schemes for retirement: NPS(market-linked+tax), SCSS(8.2%,quarterly,₹30L max,60+), POMIS(7.4%,monthly,₹9L), APY(₹1-5K pension,18-40).
- PPF(7.1%,15yr+extensions) + EPF(8.25%) = risk-free EEE retirement base. NRI: NRE FD for repatriable retirement corpus.

FORMAT: Use PRE-COMPUTED data. Show projections in a table. Explain why each number matters (e.g. why inflation changes the picture). End with: (1) corpus target with rationale (2) monthly action plan (3) recommended allocation."""

    def _normalize_monthly_expense(self, numbers: list, query: str) -> float:
        """
        Intelligently determine monthly living expenses from user's query.
        Avoids using CTC/annual income directly as monthly expense.
        """
        query_lower = query.lower()

        # Check if user explicitly said "expense" or "spend"
        explicit_expense = any(w in query_lower for w in [
            "expense", "spend", "spending", "cost", "living cost",
            "monthly expense", "monthly spend",
        ])

        # Check if this is income/CTC talk
        is_income = any(w in query_lower for w in [
            "ctc", "package", "lpa", "salary", "income", "earn",
            "per year", "per annum", "annual",
        ])

        if not numbers:
            return 50000  # default assumption

        raw = numbers[0]
        freq = self.detect_income_frequency(query)

        if explicit_expense:
            # User said "expenses ₹50K/mo" — trust it
            if freq == "annual":
                return round(raw / 12)
            return raw

        if is_income or freq == "annual" or raw >= 500000:
            # This is likely CTC/annual income, NOT monthly expense
            # Convert: CTC → take-home → estimate 50-60% as expenses
            if raw >= 100000 and (freq == "annual" or raw >= 500000):
                th = ctc_to_take_home(raw)
                monthly_take_home = th['take_home_monthly_new']
                # Assume ~60% of take-home goes to expenses
                return round(monthly_take_home * 0.60)
            else:
                # Monthly income → assume 60% as expenses
                return round(raw * 0.60)

        # For smaller numbers that look like monthly amounts
        if raw <= 200000:
            return raw

        # Fallback: if large number, assume annual income
        if raw >= 500000:
            th = ctc_to_take_home(raw)
            return round(th['take_home_monthly_new'] * 0.60)

        return raw

    def gather_context(self, query: str) -> str:
        context_parts = []

        # ── Inject relevant financial knowledge ──
        knowledge = self.get_knowledge_context(query)
        if knowledge:
            context_parts.append(knowledge)

        numbers = self.extract_numbers(query)
        query_lower = query.lower()

        if numbers:
            num_labels = [fmt_inr(n) for n in numbers]
            context_parts.append(f"EXTRACTED AMOUNTS: {', '.join(num_labels)}")

        # ── Determine monthly expense intelligently ──
        monthly_expense = self._normalize_monthly_expense(numbers, query)
        context_parts.append(
            f"ESTIMATED MONTHLY EXPENSE: {fmt_inr(monthly_expense)} "
            f"(used for retirement corpus calculation)"
        )

        # ── If income detected, show take-home first ──
        freq = self.detect_income_frequency(query)
        is_income = any(w in query_lower for w in ["ctc", "lpa", "salary", "income", "earn", "package"])
        if numbers and (is_income or freq == "annual") and numbers[0] >= 100000:
            th = ctc_to_take_home(numbers[0])
            context_parts.append(
                f"\nINCOME ANALYSIS:\n"
                f"  CTC: {fmt_inr(th['ctc_annual'])}/yr | Basic ({th['basic_pct']}%): {fmt_inr(th['basic'])}\n"
                f"  EPF (employee+employer): {fmt_inr(th['epf_employee'] + th['epf_employer_total'])}/yr\n"
                f"  Gratuity provision: {fmt_inr(th['gratuity_annual_provision'])}/yr\n"
                f"  Take-home: {fmt_inr(th['take_home_monthly_new'])}/mo (new regime)\n"
                f"  Estimated expenses (60%): {fmt_inr(monthly_expense)}/mo\n"
                f"  Available for SIP/savings: {fmt_inr(round(th['take_home_monthly_new'] - monthly_expense))}/mo\n"
                f"  Retirement accrual (EPF+Gratuity): {fmt_inr(th['total_retirement_annual'])}/yr"
            )

        # ── SIP projections ──
        if "sip" in query_lower and numbers:
            amounts = [n for n in numbers if 500 <= n <= 500000]
            monthly = amounts[0] if amounts else 10000
            context_parts.append(f"\nSIP PROJECTIONS for {fmt_inr(monthly)}/month:")
            for rate in [10, 12]:
                for y in [5, 10, 20, 30]:
                    sip_data = sip_calculator(monthly, rate, y)
                    context_parts.append(
                        f"  @{rate}% {y}yr: Invested {fmt_inr(sip_data['total_invested'])} → "
                        f"Value {fmt_inr(sip_data['future_value'])}"
                    )

        # ── Retirement corpus with NORMALIZED expense ──
        if any(w in query_lower for w in ["retire", "corpus", "fire"]) or not any(w in query_lower for w in ["sip"]):
            context_parts.append(f"\nRETIREMENT CORPUS (based on {fmt_inr(monthly_expense)}/mo expense):")
            for years_to_retire in [15, 20, 25, 30]:
                ret_data = retirement_corpus(monthly_expense, 6, years_to_retire, 30, 12)
                context_parts.append(
                    f"  Retire in {years_to_retire}yr: "
                    f"Future expense {fmt_inr(ret_data['future_monthly_expense'])}/mo, "
                    f"Corpus needed {fmt_inr(ret_data['corpus_needed'])}, "
                    f"SIP needed {fmt_inr(ret_data['monthly_sip_needed'])}/mo"
                )

        # ── Compound interest / lumpsum ──
        if any(w in query_lower for w in ["compound", "invest", "grow", "lumpsum", "lump sum"]):
            principals = [n for n in numbers if n >= 500] if numbers else []
            if principals:
                principal = principals[0]
                context_parts.append(f"\nLUMPSUM GROWTH for {fmt_inr(principal)}:")
                for rate in [8, 10, 12]:
                    for years in [5, 10, 20]:
                        ci_data = compound_interest(principal, rate, years)
                        context_parts.append(
                            f"  @{rate}% {years}yr → {fmt_inr(ci_data['final_amount'])}"
                        )

        # ── Inflation adjustment ──
        if "inflation" in query_lower:
            for nominal in [10, 12, 14]:
                inf_data = inflation_adjusted_return(nominal, 6)
                context_parts.append(f"REAL RETURN: {nominal}% nominal - 6% inflation = {inf_data['real_return']}%")

        # ── Default SIP reference if no specific query ──
        if len(context_parts) <= 2:
            context_parts.append("\nSIP REFERENCE:")
            for amt in [5000, 10000, 25000]:
                for years in [10, 30]:
                    sip_data = sip_calculator(amt, 12, years)
                    context_parts.append(
                        f"  {fmt_inr(amt)}/mo × {years}yr @12% → {fmt_inr(sip_data['future_value'])}"
                    )

        live_data = self._auto_market_data(query)
        if live_data:
            context_parts.append(f"LIVE MARKET DATA:\n{live_data}")

        return "\n\n".join(context_parts)
