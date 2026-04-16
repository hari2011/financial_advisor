"""Insurance Advisor Agent."""
import json
from agents.base import BaseAgent, fmt_inr
from tools.financial_calc import insurance_coverage


class InsuranceAdvisorAgent(BaseAgent):
    name = "Insurance Advisor (India)"
    icon = "🛡️"
    description = "Term life, health insurance, IRDAI plans, claim settlement, coverage analysis for India"

    system_prompt = """IRDAI-licensed Insurance Advisor for Indian clients. Help users understand what coverage they actually need and why — most Indians are underinsured.

APPROACH: Risk profile → Identify gaps (term/health/critical) → Calculate need → Recommend + premiums → Tax benefits.
- Term: ₹1Cr cover @30yo male ≈ ₹10-12K/yr online. Buy at 25-30 for lowest premium. Online saves 40-60%.
- Health: ₹10L floater minimum + ₹50L-1Cr super top-up (₹3-5K/yr extra). Key: restore, no co-pay, no room limit.
- NEVER: ULIPs, endowment, money-back. "Buy Term + Invest Rest" always wins.
- 80D: ₹25K self+family + ₹50K senior parents = ₹75K total. No insurance = URGENT priority.

FORMAT: Use PRE-COMPUTED data. Compare options in tables. Explain what features matter (restore benefit, co-pay, etc.) and why. End with: (1) exact coverage needed with reasoning (2) estimated annual premium (3) tax benefit under 80C/80D."""

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
            if freq == "monthly":
                annual_income = raw_income * 12
                monthly_income = raw_income
            else:
                annual_income = raw_income
                monthly_income = round(raw_income / 12)

            num_labels = [fmt_inr(n) for n in numbers]
            context_parts.append(f"EXTRACTED AMOUNTS: {', '.join(num_labels)}")

            # Pre-compute coverage for multiple dependent scenarios
            context_parts.append(f"\nINSURANCE COVERAGE ANALYSIS (Income: {fmt_inr(annual_income)}/yr):")
            for deps in [0, 1, 2, 3]:
                coverage = insurance_coverage(annual_income, deps, 0, 0)
                life_cover = coverage.get('recommended_life_cover', 0)
                health_cover = coverage.get('recommended_health_cover', 0)
                context_parts.append(
                    f"  {deps} dependents:\n"
                    f"    Term Life needed: {fmt_inr(life_cover)} ({life_cover / annual_income:.0f}x income)\n"
                    f"    Health Cover: {fmt_inr(health_cover)}"
                )

            # Pre-compute premium estimates (approx for 30yr male non-smoker)
            life_cover_15x = annual_income * 15
            life_cover_20x = annual_income * 20
            # Approx online term premium: ₹500-700 per ₹1Cr cover/year for age 30
            est_premium_15x = round(life_cover_15x / 10000000 * 600 * 12)
            est_premium_20x = round(life_cover_20x / 10000000 * 600 * 12)
            context_parts.append(
                f"\nESTIMATED ANNUAL PREMIUMS (online, age 30, non-smoker, approx):\n"
                f"  Term {fmt_inr(life_cover_15x)} (15x): ~{fmt_inr(est_premium_15x)}/yr\n"
                f"  Term {fmt_inr(life_cover_20x)} (20x): ~{fmt_inr(est_premium_20x)}/yr\n"
                f"  Health ₹10L floater: ~₹12,000-20,000/yr\n"
                f"  Health ₹25L floater: ~₹18,000-30,000/yr\n"
                f"  Super top-up ₹50L: ~₹3,000-5,000/yr"
            )

            # 80D tax benefit calculation
            context_parts.append(
                f"\n80D TAX BENEFIT:\n"
                f"  Self/Family: ₹25,000 deduction (₹50,000 if senior)\n"
                f"  Parents: ₹25,000 additional (₹50,000 if senior)\n"
                f"  Max total: ₹1,00,000 (both senior)\n"
                f"  Tax saved (30% bracket): up to ₹30,000/yr"
            )

        # Fetch latest insurance plan data
        ins_type = "term life insurance"
        for it in ["health insurance", "car insurance", "motor insurance", "travel insurance"]:
            if it in query_lower:
                ins_type = it
                break
        search_q = f"best {ins_type} India 2025 2026 plans comparison"
        web_data = self.web_lookup(search_q)
        if web_data:
            context_parts.append(f"LATEST {ins_type.upper()} DATA:\n{web_data}")

        live_data = self._auto_market_data(query)
        if live_data:
            context_parts.append(f"LIVE MARKET DATA:\n{live_data}")

        return "\n\n".join(context_parts)
