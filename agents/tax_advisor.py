"""Tax & Compliance Advisor Agent."""
import json
from agents.base import BaseAgent, fmt_inr
from tools.financial_calc import tax_bracket_us, tax_bracket_india, ctc_to_take_home
from tools.web_search import search_tax_update


class TaxAdvisorAgent(BaseAgent):
    name = "Tax & Compliance Advisor"
    icon = "🏛️"
    description = "Tax planning, deductions, tax-saving investments, compliance, capital gains"

    system_prompt = """Senior CA specializing in Indian income tax. Break down calculations clearly — users need to understand where each number comes from.

APPROACH: Understand situation → Identify deductions → Compute BOTH regimes using PRE-COMPUTED data → Recommend + actions.
- EPF at 50% Basic auto-fills 80C. NPS 80CCD(1B) extra ₹50K. 80D: ₹25K self + ₹50K senior parents = ₹75K.
- Home loan: 24(b) ₹2L interest + 80C ₹1.5L principal = ₹3.5L.
- ₹12-20L CTC: New regime almost always better (87A rebate). >20L + home loan + HRA: Old MAY win.
- FY2025-26: New regime zero-tax up to ₹12.75L effective. Std deduction: ₹75K new, ₹50K old.
- Govt schemes tax: PPF/SSY/EPF = EEE. NPS: 80CCD(1B)₹50K + partial EEE. NSC: 80C. SCSS/POMIS: taxable interest.
- NRI tax: NRE interest tax-free. NRO: 30% TDS (DTAA relief available). FCNR: tax-free. Form 15CA/15CB for remittance.

FORMAT: Use PRE-COMPUTED data. Show step-by-step: CTC→Gross→Deductions→Taxable→Tax→Cess→Net. Explain what each deduction means and who qualifies. End with: (1) regime recommendation + exact savings (2) 2-3 tax-saving actions they can take now.

IF MISSING INFO: For accurate tax computation, you NEED: income (CTC or taxable income), existing 80C investments (EPF auto-counts), HRA + rent (for old regime), home loan EMI (24b), health insurance (80D). If missing, provide preliminary computation then ask:
→ What is your annual CTC or gross salary?
→ Do you pay rent? How much? Which city? (affects HRA exemption in old regime)
→ Do you have a home loan? (Section 24b interest deduction up to ₹2L)
→ Any existing 80C investments? (ELSS, PPF, LIC, children tuition)
→ Health insurance premium? (80D: ₹25K self + ₹50K parents = ₹75K)"""

    def gather_context(self, query: str) -> str:
        context_parts = []

        # ── Inject relevant financial knowledge ──
        knowledge = self.get_knowledge_context(query)
        if knowledge:
            context_parts.append(knowledge)

        numbers = self.extract_numbers(query)
        query_lower = query.lower()

        # Auto-calculate tax if income mentioned
        if numbers:
            raw_income = max(numbers)
            freq = self.detect_income_frequency(query)
            is_ctc = any(w in query_lower for w in ["ctc", "package", "lpa"])

            # Tax calculation needs annual income
            if freq == "monthly":
                annual_income = raw_income * 12
            else:
                annual_income = raw_income
            monthly_income = annual_income / 12

            context_parts.append(
                f"INPUT: '{query.strip()[:80]}' → "
                f"Annual income: {fmt_inr(annual_income)}, Monthly: {fmt_inr(monthly_income)}"
            )

            if any(w in query_lower for w in ["us ", "usa", "dollar", "usd", "$", "american", "federal"]):
                for status in ["single", "married"]:
                    tax_data = tax_bracket_us(annual_income, status)
                    context_parts.append(f"US TAX ({status.upper()}):\n{json.dumps(tax_data, indent=2)}")
            else:
                # CTC breakdown with take-home
                if is_ctc or freq == "annual":
                    th = ctc_to_take_home(annual_income)
                    context_parts.append(
                        f"CTC → TAKE-HOME BREAKDOWN:\n"
                        f"  CTC: {fmt_inr(th['ctc_annual'])} | Basic ({th['basic_pct']}%): {fmt_inr(th['basic'])}\n"
                        f"  HRA: {fmt_inr(th['hra'])} | Special Allowance: {fmt_inr(th['special_allowance'])}\n"
                        f"  EPF (employee): {fmt_inr(th['epf_employee'])}/yr\n"
                        f"  EPF (employer): {fmt_inr(th['epf_employer_total'])}/yr"
                        f" (EPF: {fmt_inr(th['epf_employer_epf'])}, EPS: {fmt_inr(th['eps_contribution'])})\n"
                        f"  Gratuity provision: {fmt_inr(th['gratuity_annual_provision'])}/yr\n"
                        f"  Gross Salary: {fmt_inr(th['gross_salary'])}\n"
                        f"  Tax (New): {fmt_inr(th['tax_new_regime'])} (eff. {th['effective_tax_rate_new']}%)"
                        f"{' [87A REBATE - ZERO TAX]' if th.get('rebate_new') else ''}\n"
                        f"  Tax (Old): {fmt_inr(th['tax_old_regime'])} (eff. {th['effective_tax_rate_old']}%)"
                        f"{' [87A REBATE]' if th.get('rebate_old') else ''}\n"
                        f"  Take-home (New): {fmt_inr(th['take_home_monthly_new'])} /month = {fmt_inr(th['take_home_annual_new'])} /yr\n"
                        f"  Take-home (Old): {fmt_inr(th['take_home_monthly_old'])} /month = {fmt_inr(th['take_home_annual_old'])} /yr\n"
                        f"  EPF auto-fills 80C: {fmt_inr(th['epf_employee'])} of ₹1.5L limit\n"
                        f"  Retirement accrual: {fmt_inr(th['total_retirement_annual'])}/yr\n"
                        f"  Tax saved by Old Regime: {fmt_inr(th['tax_new_regime'] - th['tax_old_regime'])} "
                        f"({'Old better' if th['tax_old_regime'] < th['tax_new_regime'] else 'New better'})"
                    )
                else:
                    # Just tax slabs
                    for regime in ["new", "old"]:
                        tax_data = tax_bracket_india(annual_income, regime)
                        context_parts.append(
                            f"TAX ({regime.upper()} REGIME):\n"
                            f"  Gross: {fmt_inr(tax_data['gross_income'])}\n"
                            f"  Std deduction: {fmt_inr(tax_data['standard_deduction'])}\n"
                            f"  Taxable: {fmt_inr(tax_data['taxable_income'])}\n"
                            f"  Tax: {fmt_inr(tax_data['tax_before_cess'])} + Cess {fmt_inr(tax_data['cess_4pct'])}\n"
                            f"  Total tax: {fmt_inr(tax_data['total_tax'])} (eff. {tax_data['effective_rate']}%)"
                        )

        # Latest tax updates — only when user asks about rules/changes/latest
        if any(w in query_lower for w in ["latest", "change", "budget", "update", "new rule", "fy 2025", "fy 2026", "regime"]):
            search_q = f"{self.extract_search_keywords(query)} income tax India FY 2025-26"
            tax_search = search_tax_update(search_q)
            if tax_search and "error" not in tax_search[0]:
                context_parts.append("LATEST TAX UPDATES:")
                for r in tax_search[:2]:
                    context_parts.append(f"  • {r.get('title', '')}: {r.get('snippet', '')}")

        if not context_parts:
            context_parts.append("No income data found. Ask user for annual income or CTC.")

        live_data = self._auto_market_data(query)
        if live_data:
            context_parts.append(f"LIVE MARKET DATA:\n{live_data}")

        return "\n\n".join(context_parts)
