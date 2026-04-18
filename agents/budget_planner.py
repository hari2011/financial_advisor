"""Budget & Savings Planner Agent."""
from agents.base import BaseAgent, fmt_inr
from tools.financial_calc import sip_calculator, ctc_to_take_home, emergency_fund


class BudgetPlannerAgent(BaseAgent):
    name = "Budget & Savings Planner"
    icon = "💰"
    description = "Budgeting in ₹, expense tracking, savings goals, emergency fund, financial health"

    system_prompt = """Certified Financial Planner specializing in Indian household budgets. You MUST provide specific ₹ amounts for EVERY expense category — never just percentages.

APPROACH: Take-home (not CTC) → Family size & city tier → Fixed commitments → Itemized expense budget → Savings allocation.

MANDATORY EXPENSE CATEGORIES (always include ALL):
  1. Rent / Home loan EMI
  2. Groceries & kitchen (milk, vegetables, provisions, cooking gas)
  3. Utilities (electricity, water, internet, mobile recharge, DTH/OTT)
  4. Domestic help (maid, cook — standard in Indian middle-class households)
  5. Children's education (school fees, books, coaching/tuition, transport)
  6. Transport (fuel, car EMI, metro/bus, auto/cab)
  7. Food outside (dining, Zomato/Swiggy, office lunch)
  8. Health & medical (insurance premium, OPD, medicines, gym)
  9. Insurance (term life, health, vehicle)
  10. Personal & grooming (clothing, salon, personal care)
  11. Family support (parents' expenses, siblings — very common in India)
  12. Social & festivals (Diwali, weddings, gifts, religious donations)
  13. Entertainment & lifestyle (movies, outings, hobbies, travel fund)
  14. Miscellaneous / buffer (5% of take-home)

INDIAN FAMILY FINANCE RULES:
- Family support (parents/siblings) is NOT optional for most Indians — budget for it explicitly.
- Festivals cost ₹50K-1.5L/yr — budget monthly, not as surprises.
- Domestic help enables dual-income families — it's a necessity, not luxury.
- Education is India's #1 priority — school + coaching can be 15-25% of take-home.
- Insurance before investing: term life ₹1Cr + health ₹5L family floater = non-negotiable.
- Gold buying (₹2K-10K/mo) — use Sovereign Gold Bonds, not physical gold.

FRAMEWORKS: 50/30/20 (balanced), 60/20/20 (high-cost city), 40/20/40 (aggressive saver), 70/10/20 (low income).
Emergency fund = 6mo expenses. EPF already saves 12% Basic for retirement.
Step-up SIP +10%/yr with hikes. Even ₹5K/mo = ₹1Cr+ in 25yr @12%.

FORMAT: Use PRE-COMPUTED data. Create an itemized budget TABLE with specific ₹ amounts for EVERY category above. Show total expenses, total savings, and savings rate. End with: (1) recommended framework (2) one actionable quick win (3) areas where they may be over/under-spending vs typical Indian household.

IF MISSING INFO: For an accurate budget, you NEED to know: income (CTC or monthly), city (metro/tier-2), family size (single/couple/kids), existing EMIs, and rent. If ANY of these are missing, provide a preliminary budget with labeled assumptions, then ask:
→ What is your monthly take-home or CTC? (needed to compute actual ₹ budget)
→ Which city do you live in? (rent and expenses vary 40-60% between metro and tier-2)
→ Family size? (single / couple / family with kids)
→ Any existing EMIs? (home loan, car loan, personal loan)
→ Monthly rent amount? (largest expense category for most Indians)"""

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

            # ── Itemized Indian household expense estimation ──
            has_kids = any(w in query_lower for w in ["child", "kid", "son", "daughter",
                                                       "school", "children", "family of"])
            is_family = has_kids or any(w in query_lower for w in ["married", "wife", "husband",
                                                                    "spouse", "family", "couple"])
            is_metro = any(w in query_lower for w in ["mumbai", "delhi", "bangalore", "bengaluru",
                                                       "hyderabad", "chennai", "pune", "kolkata",
                                                       "metro", "tier 1", "tier-1"])
            is_tier2 = any(w in query_lower for w in ["tier 2", "tier-2", "tier 3", "small city",
                                                       "jaipur", "lucknow", "indore", "bhopal",
                                                       "chandigarh", "coimbatore", "kochi",
                                                       "nagpur", "patna", "ahmedabad"])

            city_factor = 0.7 if is_tier2 else 1.0  # Tier-2 costs ~70% of metro

            if is_family and has_kids:
                # Family with children
                expense_profile = {
                    "Rent / Home EMI": round(disposable * 0.22 * city_factor),
                    "Groceries & kitchen": round(min(disposable * 0.10, 18000) * city_factor),
                    "Utilities (elec/water/internet/mobile)": round(min(disposable * 0.04, 7000) * city_factor),
                    "Domestic help (maid/cook)": round(min(disposable * 0.05, 10000) * city_factor),
                    "Children education (fees/coaching/books)": round(min(disposable * 0.14, 30000)),
                    "Transport (fuel/EMI/commute)": round(min(disposable * 0.06, 12000) * city_factor),
                    "Food outside (dining/delivery)": round(min(disposable * 0.03, 6000)),
                    "Health & medical (insurance/OPD/gym)": round(min(disposable * 0.04, 8000)),
                    "Insurance (term life/health/vehicle)": round(min(disposable * 0.03, 5000)),
                    "Personal & grooming (clothing/salon)": round(min(disposable * 0.03, 6000)),
                    "Family support (parents/siblings)": round(disposable * 0.06),
                    "Social & festivals (gifts/weddings)": round(min(disposable * 0.05, 10000)),
                    "Entertainment (movies/travel fund)": round(min(disposable * 0.03, 5000)),
                    "Miscellaneous / buffer": round(disposable * 0.04),
                }
                profile_label = f"Family with children ({'Tier-2' if is_tier2 else 'Metro'})"
            elif is_family:
                # Couple without children
                expense_profile = {
                    "Rent / Home EMI": round(disposable * 0.20 * city_factor),
                    "Groceries & kitchen": round(min(disposable * 0.08, 12000) * city_factor),
                    "Utilities (elec/water/internet/mobile)": round(min(disposable * 0.04, 6000) * city_factor),
                    "Domestic help (maid/cook)": round(min(disposable * 0.04, 6000) * city_factor),
                    "Transport (fuel/EMI/commute)": round(min(disposable * 0.05, 8000) * city_factor),
                    "Food outside (dining/delivery)": round(min(disposable * 0.05, 8000)),
                    "Health & medical (insurance/OPD/gym)": round(min(disposable * 0.04, 7000)),
                    "Insurance (term life/health/vehicle)": round(min(disposable * 0.03, 4000)),
                    "Personal & grooming (clothing/salon)": round(min(disposable * 0.04, 7000)),
                    "Family support (parents/siblings)": round(disposable * 0.06),
                    "Social & festivals (gifts/weddings)": round(min(disposable * 0.05, 8000)),
                    "Entertainment (movies/travel fund)": round(min(disposable * 0.04, 6000)),
                    "Miscellaneous / buffer": round(disposable * 0.04),
                }
                profile_label = f"Couple ({'Tier-2' if is_tier2 else 'Metro'})"
            else:
                # Single person
                expense_profile = {
                    "Rent / PG / Home EMI": round(disposable * 0.25 * city_factor),
                    "Groceries & kitchen": round(min(disposable * 0.07, 8000) * city_factor),
                    "Utilities (elec/water/internet/mobile)": round(min(disposable * 0.04, 4000) * city_factor),
                    "Transport (fuel/metro/cab)": round(min(disposable * 0.05, 5000) * city_factor),
                    "Food outside (dining/Swiggy/office)": round(min(disposable * 0.07, 8000)),
                    "Health & medical (insurance/OPD/gym)": round(min(disposable * 0.03, 5000)),
                    "Insurance (term life/health)": round(min(disposable * 0.02, 3000)),
                    "Personal & grooming (clothing/salon)": round(min(disposable * 0.04, 5000)),
                    "Family support (parents/siblings)": round(disposable * 0.08),
                    "Social & festivals (gifts/weddings)": round(min(disposable * 0.04, 5000)),
                    "Entertainment (movies/travel fund)": round(min(disposable * 0.05, 6000)),
                    "Miscellaneous / buffer": round(disposable * 0.04),
                }
                profile_label = f"Single ({'Tier-2' if is_tier2 else 'Metro'})"

            total_expenses = sum(expense_profile.values())
            remaining_savings = round(disposable - total_expenses)
            savings_rate = round(remaining_savings / disposable * 100, 1) if disposable > 0 else 0

            expense_lines = [f"\nITEMIZED MONTHLY EXPENSE ESTIMATE ({profile_label}):"]
            for cat, amt in expense_profile.items():
                pct = round(amt / disposable * 100, 1) if disposable > 0 else 0
                expense_lines.append(f"  {cat}: {fmt_inr(amt)} ({pct}%)")
            expense_lines.append(f"  ─────────────────────────────")
            expense_lines.append(f"  TOTAL ESTIMATED EXPENSES: {fmt_inr(total_expenses)}")
            expense_lines.append(f"  AVAILABLE FOR SAVINGS/INVESTMENT: {fmt_inr(remaining_savings)} ({savings_rate}%)")
            expense_lines.append(f"\n  NOTE: These are realistic benchmarks for Indian households.")
            expense_lines.append(f"  Adjust based on actual lifestyle. Family support & festival costs are")
            expense_lines.append(f"  commonly underestimated — budget for them explicitly.")
            context_parts.append("\n".join(expense_lines))

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
