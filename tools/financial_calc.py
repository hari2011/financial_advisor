"""Financial calculation tools."""
import numpy as np
import numpy_financial as npf


def compound_interest(principal: float, rate: float, years: int,
                      compounding: int = 12) -> dict:
    """Calculate compound interest.
    rate: annual rate as percentage (e.g., 8 for 8%)
    compounding: times per year (12=monthly, 4=quarterly, 1=annually)
    """
    r = rate / 100
    amount = principal * (1 + r / compounding) ** (compounding * years)
    interest = amount - principal
    return {
        "principal": round(principal, 2),
        "rate": rate,
        "years": years,
        "final_amount": round(amount, 2),
        "total_interest": round(interest, 2),
        "effective_rate": round(((1 + r/compounding)**compounding - 1) * 100, 2),
    }


def sip_calculator(monthly_investment: float, annual_rate: float,
                   years: int) -> dict:
    """Calculate SIP (Systematic Investment Plan) returns."""
    r = annual_rate / 100 / 12  # Monthly rate
    n = years * 12  # Total months
    if r == 0:
        future_value = monthly_investment * n
    else:
        future_value = monthly_investment * (((1 + r) ** n - 1) / r) * (1 + r)
    total_invested = monthly_investment * n
    wealth_gained = future_value - total_invested
    return {
        "monthly_investment": round(monthly_investment, 2),
        "annual_rate": annual_rate,
        "years": years,
        "total_invested": round(total_invested, 2),
        "future_value": round(future_value, 2),
        "wealth_gained": round(wealth_gained, 2),
        "absolute_return_pct": round((wealth_gained / total_invested) * 100, 2),
    }


def emi_calculator(principal: float, annual_rate: float,
                   tenure_months: int) -> dict:
    """Calculate EMI for a loan."""
    r = annual_rate / 100 / 12
    if r == 0:
        emi = principal / tenure_months
    else:
        emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal
    return {
        "principal": round(principal, 2),
        "annual_rate": annual_rate,
        "tenure_months": tenure_months,
        "emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "interest_to_principal_ratio": round(total_interest / principal * 100, 2),
    }


def loan_amortization(principal: float, annual_rate: float,
                      tenure_months: int) -> list:
    """Generate loan amortization schedule."""
    r = annual_rate / 100 / 12
    if r == 0:
        emi = principal / tenure_months
    else:
        emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)

    balance = principal
    schedule = []
    for month in range(1, tenure_months + 1):
        interest_part = balance * r
        principal_part = emi - interest_part
        balance -= principal_part
        schedule.append({
            "month": month,
            "emi": round(emi, 2),
            "principal": round(principal_part, 2),
            "interest": round(interest_part, 2),
            "balance": round(max(balance, 0), 2),
        })
    return schedule


def cagr(beginning_value: float, ending_value: float, years: float) -> dict:
    """Calculate Compound Annual Growth Rate."""
    if beginning_value <= 0 or years <= 0:
        return {"error": "Values must be positive"}
    cagr_val = (ending_value / beginning_value) ** (1 / years) - 1
    return {
        "beginning_value": beginning_value,
        "ending_value": ending_value,
        "years": years,
        "cagr_pct": round(cagr_val * 100, 2),
    }


def npv(rate: float, cashflows: list) -> dict:
    """Calculate Net Present Value using numpy-financial.
    rate: discount rate as percentage
    cashflows: list of cash flows starting from year 0
    """
    r = rate / 100
    npv_val = float(npf.npv(r, cashflows))
    return {
        "discount_rate": rate,
        "npv": round(npv_val, 2),
        "cashflows": cashflows,
    }


def irr(cashflows: list) -> dict:
    """Calculate Internal Rate of Return using numpy-financial."""
    try:
        irr_val = float(npf.irr(cashflows))
        if np.isnan(irr_val):
            return {"error": "Could not calculate IRR for given cashflows"}
        return {"irr_pct": round(irr_val * 100, 2), "cashflows": cashflows}
    except Exception:
        return {"error": "Could not calculate IRR for given cashflows"}


def xirr(cashflows: list, dates: list) -> dict:
    """Calculate XIRR — IRR for irregular cash flows with specific dates.
    cashflows: list of amounts (negative = outflow, positive = inflow)
    dates: list of date strings 'YYYY-MM-DD' or datetime objects
    """
    from datetime import datetime as dt
    try:
        parsed_dates = []
        for d in dates:
            if isinstance(d, str):
                parsed_dates.append(dt.strptime(d, '%Y-%m-%d'))
            else:
                parsed_dates.append(d)

        # Newton's method for XIRR
        day_factors = [(d - parsed_dates[0]).days / 365.25 for d in parsed_dates]

        def xnpv(rate):
            return sum(cf / (1 + rate) ** t for cf, t in zip(cashflows, day_factors))

        def xnpv_deriv(rate):
            return sum(-t * cf / (1 + rate) ** (t + 1) for cf, t in zip(cashflows, day_factors))

        guess = 0.1
        for _ in range(1000):
            val = xnpv(guess)
            deriv = xnpv_deriv(guess)
            if abs(deriv) < 1e-12:
                break
            new_guess = guess - val / deriv
            if abs(new_guess - guess) < 1e-9:
                guess = new_guess
                break
            guess = new_guess

        return {
            "xirr_pct": round(guess * 100, 2),
            "num_cashflows": len(cashflows),
            "period_days": (parsed_dates[-1] - parsed_dates[0]).days,
        }
    except Exception as e:
        return {"error": f"XIRR calculation failed: {str(e)}"}


def rule_of_72(rate: float) -> dict:
    """Estimate doubling time using Rule of 72."""
    if rate <= 0:
        return {"error": "Rate must be positive"}
    years = 72 / rate
    return {
        "rate": rate,
        "years_to_double": round(years, 1),
        "doubling_years": round(years, 1),
        "explanation": f"At {rate}% annual return, your money doubles in ~{years:.1f} years",
    }


def inflation_adjusted_return(nominal_rate: float, inflation_rate: float) -> dict:
    """Calculate real (inflation-adjusted) return."""
    real_rate = ((1 + nominal_rate/100) / (1 + inflation_rate/100) - 1) * 100
    return {
        "nominal_rate": nominal_rate,
        "inflation_rate": inflation_rate,
        "real_return": round(real_rate, 2),
    }


def retirement_corpus(monthly_expense: float, inflation_rate: float,
                      years_to_retire: int, years_in_retirement: int,
                      expected_return: float) -> dict:
    """Calculate retirement corpus needed.
    monthly_expense: Current MONTHLY living expenses (NOT income, NOT annual).
    """
    # Sanity check: monthly expense > ₹5L is suspicious (likely annual income passed as monthly)
    if monthly_expense > 500000:
        import logging
        logging.getLogger('financegpt.calc').warning(
            f'retirement_corpus called with monthly_expense={monthly_expense:.0f} '
            f'(>₹5L/mo). This may be annual income mistakenly passed as monthly expense.'
        )
    # Future monthly expense at retirement
    future_expense = monthly_expense * (1 + inflation_rate/100) ** years_to_retire
    annual_expense = future_expense * 12

    # Corpus needed (using annuity formula adjusted for inflation)
    real_return = ((1 + expected_return/100) / (1 + inflation_rate/100) - 1)
    if real_return <= 0:
        corpus = annual_expense * years_in_retirement
    else:
        corpus = annual_expense * (1 - (1 + real_return) ** -years_in_retirement) / real_return

    # Monthly SIP needed
    monthly_rate = expected_return / 100 / 12
    n = years_to_retire * 12
    if monthly_rate == 0:
        monthly_sip = corpus / n
    else:
        monthly_sip = corpus * monthly_rate / ((1 + monthly_rate) ** n - 1)

    return {
        "current_monthly_expense": round(monthly_expense, 2),
        "future_monthly_expense": round(future_expense, 2),
        "corpus_needed": round(corpus, 2),
        "monthly_sip_needed": round(monthly_sip, 2),
        "years_to_retire": years_to_retire,
        "years_in_retirement": years_in_retirement,
    }


def portfolio_return(holdings: list) -> dict:
    """Calculate weighted portfolio return.
    holdings: list of (weight, return) tuples OR dicts with 'weight' and 'return' keys.
    """
    # Support both tuples and dicts
    def _get(h):
        if isinstance(h, (tuple, list)):
            return h[0], h[1]
        return h["weight"], h["return"]

    total_weight = sum(_get(h)[0] for h in holdings)
    if abs(total_weight - 100) > 0.01:
        return {"error": f"Weights must sum to 100%, got {total_weight}%"}

    portfolio_ret = sum(_get(h)[0] * _get(h)[1] / 100 for h in holdings)
    return {
        "holdings": holdings,
        "portfolio_return": round(portfolio_ret, 2),
        "portfolio_return_pct": round(portfolio_ret, 2),
    }


def tax_bracket_us(taxable_income: float, filing_status: str = "single") -> dict:
    """Calculate US federal income tax (2024 brackets)."""
    brackets_single = [
        (11600, 0.10), (47150, 0.12), (100525, 0.22),
        (191950, 0.24), (243725, 0.32), (609350, 0.35),
        (float('inf'), 0.37),
    ]
    brackets_married = [
        (23200, 0.10), (94300, 0.12), (201050, 0.22),
        (383900, 0.24), (487450, 0.32), (731200, 0.35),
        (float('inf'), 0.37),
    ]
    brackets = brackets_married if "married" in filing_status.lower() else brackets_single
    std_deduction = 29200 if "married" in filing_status.lower() else 14600

    taxable = max(0, taxable_income - std_deduction)
    tax = 0
    prev_limit = 0
    breakdown = []
    for limit, rate in brackets:
        if taxable <= 0:
            break
        amount_in_bracket = min(taxable, limit - prev_limit)
        tax_in_bracket = amount_in_bracket * rate
        tax += tax_in_bracket
        if amount_in_bracket > 0:
            breakdown.append({
                "bracket": f"{rate*100:.0f}%",
                "income_in_bracket": round(amount_in_bracket, 2),
                "tax": round(tax_in_bracket, 2),
            })
        taxable -= amount_in_bracket
        prev_limit = limit

    effective_rate = (tax / taxable_income * 100) if taxable_income > 0 else 0
    return {
        "gross_income": round(taxable_income, 2),
        "standard_deduction": std_deduction,
        "taxable_income": round(max(0, taxable_income - std_deduction), 2),
        "total_tax": round(tax, 2),
        "effective_rate": round(effective_rate, 2),
        "marginal_rate": breakdown[-1]["bracket"] if breakdown else "0%",
        "breakdown": breakdown,
        "filing_status": filing_status,
    }


def tax_bracket_india(taxable_income: float, regime: str = "new") -> dict:
    """Calculate Indian income tax (new/old regime FY 2025-26).
    New regime: Updated slabs per Budget 2025.
    """
    if regime == "new":
        brackets = [
            (400000, 0), (800000, 0.05), (1200000, 0.10),
            (1600000, 0.15), (2000000, 0.20), (2400000, 0.25),
            (float('inf'), 0.30),
        ]
        std_deduction = 75000
        rebate_limit = 1200000  # Rebate u/s 87A: zero tax if income ≤ ₹12L
    else:
        brackets = [
            (250000, 0), (500000, 0.05), (1000000, 0.20),
            (float('inf'), 0.30),
        ]
        std_deduction = 50000
        rebate_limit = 500000  # Old regime 87A: rebate if income ≤ ₹5L

    taxable = max(0, taxable_income - std_deduction)

    # Check rebate eligibility
    rebate_eligible = taxable <= rebate_limit

    tax = 0
    prev_limit = 0
    breakdown = []
    for limit, rate in brackets:
        if taxable <= 0:
            break
        amount = min(taxable, limit - prev_limit)
        t = amount * rate
        tax += t
        if amount > 0 and rate > 0:
            breakdown.append({
                "bracket": f"{rate*100:.0f}%",
                "income": round(amount, 2),
                "tax": round(t, 2),
            })
        taxable -= amount
        prev_limit = limit

    # Apply rebate u/s 87A
    if rebate_eligible:
        tax = 0
        breakdown = []

    # Health & Education Cess 4%
    cess = tax * 0.04
    total = tax + cess
    effective = (total / taxable_income * 100) if taxable_income > 0 else 0

    return {
        "gross_income": round(taxable_income, 2),
        "standard_deduction": std_deduction,
        "taxable_income": round(max(0, taxable_income - std_deduction), 2),
        "rebate_87a": rebate_eligible,
        "tax_before_cess": round(tax, 2),
        "cess_4pct": round(cess, 2),
        "total_tax": round(total, 2),
        "effective_rate": round(effective, 2),
        "regime": regime,
        "breakdown": breakdown,
    }


def ctc_to_take_home(ctc_annual: float, basic_pct: float = 0.50,
                     epf_on_full_basic: bool = True,
                     additional_80c: float = 0,
                     nps_employer_pct: float = 0) -> dict:
    """Given annual CTC, compute detailed salary breakdown and take-home.

    Covers: Basic, HRA, Special Allowance, EPF (with EPS split + wage ceiling),
    Gratuity provision (with eligibility & tax rules), Professional Tax,
    Income Tax (both regimes with proper deductions).

    Indian EPF rules (2024-25):
    - Employee: 12% of Basic+DA (statutory ceiling ₹15,000/mo, but many companies
      voluntarily contribute on full basic for better retirement benefits)
    - Employer: 12% of Basic+DA, split as:
      * 8.33% → EPS (Pension) capped at Basic ₹15,000/mo i.e. max ₹1,250/mo
      * Remainder → EPF account
    - EDLI: 0.50% of Basic (capped ₹15,000/mo), paid by employer (part of CTC)

    Gratuity rules:
    - Formula: (Basic_monthly × 15 × Years) / 26
    - Eligible after 5 years continuous service
    - Tax exempt up to ₹20,00,000
    - Companies provision ~4.81% of Basic annually in CTC

    Args:
        ctc_annual: Annual CTC in rupees
        basic_pct: Basic as fraction of CTC (default 0.50 per new Wage Code)
        epf_on_full_basic: If True, EPF on full basic; if False, cap at ₹15,000/mo
        additional_80c: Additional 80C investments beyond EPF (ELSS, PPF, LIC, etc.)
        nps_employer_pct: Employer NPS contribution as % of basic (0-14%, deductible in new regime)
    """
    basic = ctc_annual * basic_pct
    basic_monthly = basic / 12
    hra = basic * 0.50  # 50% of Basic (metro default)

    # ── EPF Contributions ──
    # Statutory wage ceiling: ₹15,000/month
    EPF_WAGE_CEILING_MONTHLY = 15000
    epf_wage_ceiling_annual = EPF_WAGE_CEILING_MONTHLY * 12  # ₹1,80,000

    if epf_on_full_basic:
        epf_basic = basic  # Apply on full basic
    else:
        epf_basic = min(basic, epf_wage_ceiling_annual)  # Cap at ₹15K/mo

    epf_employee = epf_basic * 0.12              # 12% from employee salary
    epf_employer_total = epf_basic * 0.12        # 12% from employer (part of CTC)

    # EPS: 8.33% of Basic, ALWAYS capped at ₹15,000/mo regardless of epf_on_full_basic
    eps_basic_capped = min(basic, epf_wage_ceiling_annual)
    eps_contribution = eps_basic_capped * 0.0833  # Max ₹1,250/mo = ₹14,994/yr
    epf_employer_to_epf = epf_employer_total - eps_contribution  # Rest goes to EPF account

    # EDLI (Employer Deposit-Linked Insurance): 0.50% of Basic (capped at ₹15K/mo)
    edli = min(basic, epf_wage_ceiling_annual) * 0.005

    # ── NPS (if applicable) ──
    nps_employer = basic * (nps_employer_pct / 100) if nps_employer_pct else 0

    # ── Gratuity Provision ──
    # Annual provision: (Basic_monthly × 15) / 26
    # This equals ~4.81% of Basic per year of service
    gratuity_annual = (basic_monthly * 15) / 26
    # Actual gratuity at various milestones (for display)
    gratuity_5yr = (basic_monthly * 15 * 5) / 26   # Minimum eligible
    gratuity_10yr = (basic_monthly * 15 * 10) / 26
    gratuity_20yr = (basic_monthly * 15 * 20) / 26
    GRATUITY_TAX_EXEMPT_LIMIT = 2000000  # ₹20L exempt under Section 10(10)

    # ── Special Allowance ──
    # CTC = Basic + HRA + Employer EPF + EDLI + Gratuity + NPS_employer + Special
    special_allowance = (ctc_annual - basic - hra - epf_employer_total
                         - edli - gratuity_annual - nps_employer)

    # ── Gross Salary ──
    # Gross = CTC minus employer-only costs
    employer_costs = epf_employer_total + edli + gratuity_annual + nps_employer
    gross_salary = ctc_annual - employer_costs

    # ── Professional Tax ──
    # Standard across most states (Karnataka ₹2,400, Maharashtra ₹2,500, etc.)
    professional_tax = 2400

    # ── Income Tax (New Regime) ──
    # New regime: Standard deduction ₹75,000 only, no 80C/80D deductions
    # But NPS employer contribution (up to 14% basic) is deductible
    new_regime_deduction = nps_employer  # Only NPS employer in new regime
    new_taxable = gross_salary - new_regime_deduction
    new_tax = tax_bracket_india(new_taxable, "new")

    # ── Income Tax (Old Regime) ──
    # Old regime: Standard deduction ₹50,000 + Section 80C (₹1.5L cap) + 80CCD(2) NPS
    # EPF employee contribution auto-qualifies for 80C
    section_80c_total = min(epf_employee + additional_80c, 150000)
    section_80ccd2_nps = nps_employer  # Employer NPS - no cap in old regime (above 80C)
    old_regime_deduction = section_80c_total + section_80ccd2_nps
    old_taxable = gross_salary - old_regime_deduction
    old_tax = tax_bracket_india(old_taxable, "old")

    # ── Take-Home ──
    take_home_new = gross_salary - epf_employee - professional_tax - new_tax["total_tax"]
    take_home_old = gross_salary - epf_employee - professional_tax - old_tax["total_tax"]

    # ── Retirement Benefits Total ──
    total_retirement_annual = epf_employee + epf_employer_total + gratuity_annual

    # ── Monthly breakdown ──
    monthly_basic = round(basic / 12)
    monthly_hra = round(hra / 12)
    monthly_special = round(max(0, special_allowance) / 12)
    monthly_epf_employee = round(epf_employee / 12)
    monthly_epf_employer = round(epf_employer_total / 12)
    monthly_gross = round(gross_salary / 12)
    monthly_professional_tax = round(professional_tax / 12)

    return {
        "ctc_annual": round(ctc_annual),
        "basic_pct": round(basic_pct * 100),
        "basic": round(basic),
        "basic_monthly": monthly_basic,
        "hra": round(hra),
        "hra_monthly": monthly_hra,
        "special_allowance": round(max(0, special_allowance)),
        "special_allowance_monthly": monthly_special,

        # EPF details
        "epf_on_full_basic": epf_on_full_basic,
        "epf_basic": round(epf_basic),
        "epf_wage_ceiling": epf_wage_ceiling_annual,
        "epf_employee": round(epf_employee),
        "epf_employee_monthly": monthly_epf_employee,
        "epf_employer_total": round(epf_employer_total),
        "epf_employer_monthly": monthly_epf_employer,
        "epf_employer_epf": round(epf_employer_to_epf),   # Employer's share → EPF account
        "eps_contribution": round(eps_contribution),        # Employer's share → EPS (pension)
        "eps_monthly": round(eps_contribution / 12),
        "edli": round(edli),

        # NPS
        "nps_employer": round(nps_employer),

        # Gratuity
        "gratuity_annual_provision": round(gratuity_annual),
        "gratuity_monthly_provision": round(gratuity_annual / 12),
        "gratuity_5yr": round(gratuity_5yr),
        "gratuity_10yr": round(gratuity_10yr),
        "gratuity_20yr": round(gratuity_20yr),
        "gratuity_tax_exempt_limit": GRATUITY_TAX_EXEMPT_LIMIT,

        # Gross & Tax
        "gross_salary": round(gross_salary),
        "gross_monthly": monthly_gross,
        "professional_tax": professional_tax,
        "professional_tax_monthly": monthly_professional_tax,

        # Old regime deductions
        "section_80c_auto_epf": round(min(epf_employee, 150000)),
        "section_80c_total": round(section_80c_total),
        "section_80c_remaining": round(max(0, 150000 - epf_employee)),

        # Tax
        "tax_new_regime": round(new_tax["total_tax"]),
        "tax_new_monthly": round(new_tax["total_tax"] / 12),
        "tax_old_regime": round(old_tax["total_tax"]),
        "tax_old_monthly": round(old_tax["total_tax"] / 12),
        "rebate_new": new_tax.get("rebate_87a", False),
        "rebate_old": old_tax.get("rebate_87a", False),

        # Take-home
        "take_home_annual_new": round(take_home_new),
        "take_home_annual_old": round(take_home_old),
        "take_home_monthly_new": round(take_home_new / 12),
        "take_home_monthly_old": round(take_home_old / 12),
        "effective_tax_rate_new": round(new_tax["effective_rate"], 1),
        "effective_tax_rate_old": round(old_tax["effective_rate"], 1),

        # Retirement accrual
        "total_retirement_annual": round(total_retirement_annual),
        "total_retirement_monthly": round(total_retirement_annual / 12),

        # Total employee deductions per month (EPF + PT + Tax)
        "total_deductions_monthly_new": round((epf_employee + professional_tax + new_tax["total_tax"]) / 12),
        "total_deductions_monthly_old": round((epf_employee + professional_tax + old_tax["total_tax"]) / 12),

        # Legacy keys (backward compatibility)
        "basic_40pct": round(basic),
        "hra_20pct": round(hra),
        "epf_employee_12pct": round(epf_employee),
        "epf_employer_12pct": round(epf_employer_total),
    }


def emergency_fund(monthly_expenses: float, months: int = 6) -> dict:
    """Calculate recommended emergency fund."""
    amount = round(monthly_expenses * months, 2)
    return {
        "monthly_expenses": monthly_expenses,
        "months_coverage": months,
        "emergency_fund_amount": amount,
        "emergency_fund_needed": amount,
    }


def debt_to_income(monthly_debt: float, monthly_income: float) -> dict:
    """Calculate debt-to-income ratio."""
    ratio = (monthly_debt / monthly_income * 100) if monthly_income > 0 else 0
    if ratio < 20:
        status = "Excellent - You have very manageable debt levels"
    elif ratio < 36:
        status = "Good - Your debt is within acceptable limits"
    elif ratio < 43:
        status = "Concerning - Consider reducing debt"
    else:
        status = "High Risk - Urgent debt reduction recommended"
    return {
        "monthly_debt": monthly_debt,
        "monthly_income": monthly_income,
        "dti_ratio": round(ratio, 2),
        "status": status,
    }


def savings_rate(monthly_income: float, monthly_savings: float) -> dict:
    """Calculate savings rate."""
    rate = (monthly_savings / monthly_income * 100) if monthly_income > 0 else 0
    if rate >= 30:
        assessment = "Excellent - Aggressive saver on track for early financial freedom"
    elif rate >= 20:
        assessment = "Good - Solid savings habit"
    elif rate >= 10:
        assessment = "Fair - Room for improvement"
    else:
        assessment = "Low - Try to increase savings, target at least 20%"
    return {
        "monthly_income": monthly_income,
        "monthly_savings": monthly_savings,
        "savings_rate_pct": round(rate, 2),
        "assessment": assessment,
    }


def insurance_coverage(annual_income: float, dependents: int,
                       existing_coverage: float = 0,
                       outstanding_loans: float = 0) -> dict:
    """Calculate recommended life and health insurance coverage."""
    # Human Life Value method for life cover
    multiplier = 10 + (dependents * 2)
    recommended_life = annual_income * multiplier + outstanding_loans
    gap = max(0, recommended_life - existing_coverage)
    # Health cover recommendation: base ₹10L + ₹5L per dependent
    recommended_health = 1000000 + (dependents * 500000)
    return {
        "annual_income": annual_income,
        "dependents": dependents,
        "multiplier": multiplier,
        "recommended_life_cover": round(recommended_life, 2),
        "recommended_health_cover": round(recommended_health, 2),
        "recommended_coverage": round(recommended_life, 2),
        "existing_coverage": existing_coverage,
        "coverage_gap": round(gap, 2),
        "outstanding_loans": outstanding_loans,
    }


# ═══════════════════════════════════════════════════════════════════
# ENHANCED CALCULATORS — Deep Financial Intelligence
# ═══════════════════════════════════════════════════════════════════

def hra_exemption(basic_annual: float, hra_received: float,
                  rent_paid_annual: float, metro: bool = True) -> dict:
    """Calculate HRA exemption under old regime — 3-way minimum rule.

    HRA exemption = MIN of:
      1. Actual HRA received
      2. Rent paid − 10% of Basic
      3. 50% of Basic (metro) or 40% of Basic (non-metro)

    Only applicable under OLD tax regime.
    """
    pct = 0.50 if metro else 0.40
    option1 = hra_received
    option2 = max(0, rent_paid_annual - basic_annual * 0.10)
    option3 = basic_annual * pct

    exemption = min(option1, option2, option3)
    taxable_hra = hra_received - exemption

    return {
        "basic_annual": round(basic_annual),
        "hra_received": round(hra_received),
        "rent_paid_annual": round(rent_paid_annual),
        "metro_city": metro,
        "option1_actual_hra": round(option1),
        "option2_rent_minus_10pct": round(option2),
        "option3_50_or_40_pct_basic": round(option3),
        "hra_exemption": round(exemption),
        "taxable_hra": round(taxable_hra),
        "annual_tax_saving_approx": round(taxable_hra * 0.30 * 1.04) if taxable_hra > 0 else 0,
    }


def stepup_sip(monthly_sip: float, annual_rate: float, years: int,
               annual_stepup_pct: float = 10.0) -> dict:
    """SIP with annual step-up (increment).

    Each year the SIP amount increases by stepup_pct%.
    This mirrors salary increments and dramatically improves corpus.
    """
    r = annual_rate / 100 / 12
    total_invested = 0
    corpus = 0
    yearly_breakdown = []

    for yr in range(1, years + 1):
        current_sip = monthly_sip * (1 + annual_stepup_pct / 100) ** (yr - 1)
        for _ in range(12):
            corpus = (corpus + current_sip) * (1 + r)
            total_invested += current_sip
        yearly_breakdown.append({
            "year": yr,
            "monthly_sip": round(current_sip),
            "corpus": round(corpus),
        })

    # Compare with flat SIP
    flat_corpus = monthly_sip * (((1 + r) ** (years * 12) - 1) / r) * (1 + r) if r > 0 else monthly_sip * years * 12

    return {
        "initial_monthly_sip": round(monthly_sip),
        "annual_stepup_pct": annual_stepup_pct,
        "annual_rate": annual_rate,
        "years": years,
        "total_invested": round(total_invested),
        "final_corpus": round(corpus),
        "wealth_gained": round(corpus - total_invested),
        "flat_sip_corpus": round(flat_corpus),
        "stepup_advantage": round(corpus - flat_corpus),
        "stepup_advantage_pct": round((corpus - flat_corpus) / flat_corpus * 100, 1) if flat_corpus > 0 else 0,
        "final_monthly_sip": round(monthly_sip * (1 + annual_stepup_pct / 100) ** (years - 1)),
        "milestones": [b for b in yearly_breakdown if b["year"] in (1, 5, 10, 15, 20, 25, 30) and b["year"] <= years],
    }


def goal_sip(target_amount: float, annual_rate: float, years: int) -> dict:
    """Reverse SIP — how much monthly SIP needed to reach a target corpus."""
    r = annual_rate / 100 / 12
    n = years * 12
    if r == 0:
        monthly_sip = target_amount / n
    else:
        monthly_sip = target_amount * r / (((1 + r) ** n - 1) * (1 + r))

    total_invested = monthly_sip * n
    return {
        "target_amount": round(target_amount),
        "annual_rate": annual_rate,
        "years": years,
        "monthly_sip_needed": round(monthly_sip),
        "total_investment": round(total_invested),
        "wealth_from_returns": round(target_amount - total_invested),
        "return_multiplier": round(target_amount / total_invested, 2) if total_invested > 0 else 0,
    }


def loan_prepayment(principal: float, annual_rate: float,
                    tenure_months: int, prepay_amount: float,
                    prepay_after_months: int = 12,
                    reduce: str = "tenure") -> dict:
    """Impact of loan prepayment — reduce tenure or reduce EMI.

    Args:
        reduce: 'tenure' (keep EMI, shorter loan) or 'emi' (keep tenure, lower EMI)
    """
    r = annual_rate / 100 / 12
    if r == 0:
        return {"error": "Cannot compute prepayment for 0% rate"}

    # Original EMI
    emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    total_original = emi * tenure_months

    # Balance after prepay_after_months
    balance = principal
    interest_paid_before = 0
    for _ in range(prepay_after_months):
        interest = balance * r
        interest_paid_before += interest
        balance -= (emi - interest)

    # Apply prepayment
    balance_after_prepay = max(0, balance - prepay_amount)

    if reduce == "tenure":
        # Keep same EMI, find new tenure
        if balance_after_prepay <= 0:
            new_tenure = 0
            new_emi = emi
        else:
            import math
            new_tenure = math.ceil(
                -math.log(1 - balance_after_prepay * r / emi) / math.log(1 + r)
            )
            new_emi = emi
        total_new = (prepay_after_months * emi) + prepay_amount + (new_tenure * emi)
        months_saved = tenure_months - prepay_after_months - new_tenure
    else:  # reduce EMI
        remaining = tenure_months - prepay_after_months
        if balance_after_prepay <= 0:
            new_emi = 0
            new_tenure = remaining
        else:
            new_emi = balance_after_prepay * r * (1 + r) ** remaining / ((1 + r) ** remaining - 1)
            new_tenure = remaining
        total_new = (prepay_after_months * emi) + prepay_amount + (new_tenure * new_emi)
        months_saved = 0

    interest_saved = total_original - total_new

    return {
        "original_emi": round(emi),
        "original_tenure_months": tenure_months,
        "original_total_cost": round(total_original),
        "original_total_interest": round(total_original - principal),
        "prepay_amount": round(prepay_amount),
        "prepay_after_months": prepay_after_months,
        "balance_at_prepay": round(balance),
        "balance_after_prepay": round(balance_after_prepay),
        "strategy": reduce,
        "new_emi": round(new_emi) if reduce == "emi" else round(emi),
        "new_remaining_months": new_tenure if reduce == "tenure" else (tenure_months - prepay_after_months),
        "months_saved": months_saved if reduce == "tenure" else 0,
        "years_saved": round(months_saved / 12, 1) if reduce == "tenure" else 0,
        "total_new_cost": round(total_new),
        "interest_saved": round(max(0, interest_saved)),
        "emi_reduction": round(emi - new_emi) if reduce == "emi" else 0,
    }


def capital_gains_tax(purchase_price: float, sale_price: float,
                      holding_period_months: int,
                      asset_type: str = "equity") -> dict:
    """Calculate capital gains tax for Indian investors (FY 2025-26).

    asset_type: 'equity' | 'equity_mf' | 'debt_mf' | 'gold' | 'property' | 'crypto'
    """
    gain = sale_price - purchase_price
    if gain <= 0:
        return {
            "purchase_price": round(purchase_price),
            "sale_price": round(sale_price),
            "gain": round(gain),
            "tax": 0,
            "net_gain": round(gain),
            "asset_type": asset_type,
            "holding_period_months": holding_period_months,
            "type": "Loss — can set off against gains",
        }

    at = asset_type.lower()

    if at in ("equity", "equity_mf"):
        if holding_period_months >= 12:
            # LTCG: 12.5% above ₹1.25L exemption
            taxable_gain = max(0, gain - 125000)
            tax = taxable_gain * 0.125
            tax_type = "LTCG @12.5% (₹1.25L exempt)"
        else:
            # STCG: flat 20%
            tax = gain * 0.20
            tax_type = "STCG @20%"

    elif at == "debt_mf":
        # Debt MF: taxed at slab rate regardless of holding period (post Apr 2023)
        tax = gain * 0.30  # Assume 30% slab (highest)
        tax_type = "Taxed at slab rate (assumed 30%)"

    elif at == "gold":
        if holding_period_months >= 24:
            # Gold LTCG: 12.5% (no indexation post July 2024)
            tax = gain * 0.125
            tax_type = "LTCG @12.5% (gold, >24mo)"
        else:
            tax = gain * 0.30
            tax_type = "STCG at slab rate (assumed 30%)"

    elif at == "property":
        if holding_period_months >= 24:
            # Property LTCG: 12.5% (no indexation post July 2024)
            tax = gain * 0.125
            tax_type = "LTCG @12.5% (property, >24mo)"
        else:
            tax = gain * 0.30
            tax_type = "STCG at slab rate (assumed 30%)"

    elif at == "crypto":
        # Crypto: flat 30% + 1% TDS on sale
        tax = gain * 0.30
        tds = sale_price * 0.01
        cess = tax * 0.04
        return {
            "purchase_price": round(purchase_price),
            "sale_price": round(sale_price),
            "gain": round(gain),
            "tax_30pct": round(tax),
            "cess_4pct": round(cess),
            "tds_1pct_on_sale": round(tds),
            "total_tax": round(tax + cess),
            "net_gain": round(gain - tax - cess),
            "effective_tax_rate": round((tax + cess) / gain * 100, 1),
            "asset_type": "crypto",
            "type": "Flat 30% + 4% cess (no deductions except acquisition cost)",
        }
    else:
        tax = gain * 0.30
        tax_type = "Default slab rate (30%)"

    cess = tax * 0.04
    total_tax = tax + cess

    return {
        "purchase_price": round(purchase_price),
        "sale_price": round(sale_price),
        "gain": round(gain),
        "holding_period_months": holding_period_months,
        "tax_before_cess": round(tax),
        "cess_4pct": round(cess),
        "total_tax": round(total_tax),
        "net_gain": round(gain - total_tax),
        "effective_tax_rate": round(total_tax / gain * 100, 1) if gain > 0 else 0,
        "asset_type": asset_type,
        "type": tax_type,
    }


def section_80c_optimizer(epf_employee: float = 0, ppf: float = 0,
                          elss: float = 0, life_insurance: float = 0,
                          nps_50ccd1: float = 0, others_80c: float = 0,
                          nps_80ccd1b: float = 0, health_80d_self: float = 0,
                          health_80d_parents: float = 0,
                          home_loan_interest: float = 0,
                          education_loan_interest: float = 0) -> dict:
    """Optimize all major tax deductions under Old Regime.

    80C: ₹1.5L cap (EPF + PPF + ELSS + LI + NPS 10% + others)
    80CCD(1B): ₹50K extra for NPS
    80D: ₹25K self+family (+₹25K/₹50K for parents)
    24(b): ₹2L home loan interest
    80E: Full education loan interest (no cap)
    """
    # 80C optimization
    total_80c = epf_employee + ppf + elss + life_insurance + nps_50ccd1 + others_80c
    cap_80c = 150000
    eligible_80c = min(total_80c, cap_80c)
    unused_80c = max(0, cap_80c - total_80c)

    # 80CCD(1B) — NPS extra
    eligible_80ccd1b = min(nps_80ccd1b, 50000)

    # 80D — Health insurance
    cap_self = 25000  # 50000 if senior citizen
    cap_parents = 50000  # assuming parents are senior citizens
    eligible_80d_self = min(health_80d_self, cap_self)
    eligible_80d_parents = min(health_80d_parents, cap_parents)
    eligible_80d = eligible_80d_self + eligible_80d_parents

    # 24(b) — Home loan interest
    eligible_24b = min(home_loan_interest, 200000)

    # 80E — Education loan interest (no cap, 8 years from start of repayment)
    eligible_80e = education_loan_interest

    total_deductions = eligible_80c + eligible_80ccd1b + eligible_80d + eligible_24b + eligible_80e
    estimated_tax_saved = total_deductions * 0.312  # 30% + 4% cess

    suggestions = []
    if unused_80c > 0:
        suggestions.append(f"Invest ₹{unused_80c:,.0f} more in ELSS/PPF to max 80C")
    if nps_80ccd1b == 0:
        suggestions.append("Invest ₹50,000 in NPS for extra 80CCD(1B) deduction")
    if health_80d_self == 0:
        suggestions.append("Get health insurance: ₹25K deduction under 80D")
    if health_80d_parents == 0:
        suggestions.append("Parents' health insurance: up to ₹50K under 80D")

    return {
        "section_80c": {
            "epf": round(epf_employee), "ppf": round(ppf),
            "elss": round(elss), "life_insurance": round(life_insurance),
            "nps_80c": round(nps_50ccd1), "others": round(others_80c),
            "total_claimed": round(total_80c),
            "eligible": round(eligible_80c),
            "unused": round(unused_80c),
        },
        "section_80ccd1b_nps": round(eligible_80ccd1b),
        "section_80d_health": round(eligible_80d),
        "section_24b_home_loan": round(eligible_24b),
        "section_80e_edu_loan": round(eligible_80e),
        "total_deductions": round(total_deductions),
        "estimated_tax_saved": round(estimated_tax_saved),
        "suggestions": suggestions,
    }


def rent_vs_buy(property_price: float, monthly_rent: float,
                loan_rate: float = 8.5, loan_tenure_years: int = 20,
                down_payment_pct: float = 20,
                property_appreciation: float = 5.0,
                rent_increase_pct: float = 5.0,
                investment_return: float = 12.0,
                years: int = 20) -> dict:
    """Rent vs Buy analysis — compares total cost of ownership vs renting + investing.

    Factors: EMI, maintenance, property tax, opportunity cost of down payment,
    rent escalation, investment returns on difference.
    """
    down_payment = property_price * down_payment_pct / 100
    loan_amount = property_price - down_payment
    r = loan_rate / 100 / 12
    n = loan_tenure_years * 12

    if r > 0:
        emi = loan_amount * r * (1 + r) ** n / ((1 + r) ** n - 1)
    else:
        emi = loan_amount / n

    # Buy scenario
    total_emi = emi * n
    total_interest = total_emi - loan_amount
    maintenance = property_price * 0.01  # 1% annual maintenance
    property_tax_annual = property_price * 0.002  # 0.2% property tax
    registration = property_price * 0.07  # ~7% stamp duty + registration
    total_buy_cost = down_payment + total_emi + registration + (maintenance + property_tax_annual) * years
    future_property_value = property_price * (1 + property_appreciation / 100) ** years

    # Rent scenario
    total_rent = 0
    current_rent = monthly_rent * 12
    for yr in range(years):
        total_rent += current_rent
        current_rent *= (1 + rent_increase_pct / 100)
    # Invest the difference (down payment + registration + EMI-rent difference)
    monthly_invest_return = investment_return / 100 / 12
    # Invest down payment + registration as lumpsum
    lumpsum_growth = (down_payment + registration) * (1 + investment_return / 100) ** years
    # Monthly savings = EMI - rent (when EMI > rent)
    surplus_corpus = 0
    current_monthly_rent = monthly_rent
    for month in range(years * 12):
        if month > 0 and month % 12 == 0:
            current_monthly_rent *= (1 + rent_increase_pct / 100)
        monthly_surplus = max(0, emi + maintenance / 12 - current_monthly_rent)
        surplus_corpus = (surplus_corpus + monthly_surplus) * (1 + monthly_invest_return)

    total_rent_wealth = lumpsum_growth + surplus_corpus

    buy_net = future_property_value - total_buy_cost
    rent_net = total_rent_wealth - total_rent

    better = "BUY" if buy_net > rent_net else "RENT"

    return {
        "property_price": round(property_price),
        "down_payment": round(down_payment),
        "loan_amount": round(loan_amount),
        "emi": round(emi),
        "monthly_rent": round(monthly_rent),
        "buy_total_cost": round(total_buy_cost),
        "buy_property_value_after": round(future_property_value),
        "buy_net_position": round(buy_net),
        "rent_total_paid": round(total_rent),
        "rent_investment_corpus": round(total_rent_wealth),
        "rent_net_position": round(rent_net),
        "recommendation": better,
        "advantage_amount": round(abs(buy_net - rent_net)),
        "years_analysed": years,
        "key_assumptions": f"Property appreciation {property_appreciation}%, Rent hike {rent_increase_pct}%, Investment return {investment_return}%",
    }


def ppf_calculator(annual_deposit: float, years: int = 15,
                   current_rate: float = 7.1) -> dict:
    """PPF Calculator — 15yr lock-in, ₹1.5L/yr max, EEE tax benefit.

    PPF allows partial withdrawal from 7th year and extension in 5-year blocks.
    """
    annual_deposit = min(annual_deposit, 150000)  # PPF cap
    balance = 0
    total_invested = 0
    interest_earned = 0
    yearly = []

    for yr in range(1, years + 1):
        balance += annual_deposit
        total_invested += annual_deposit
        yr_interest = balance * current_rate / 100
        interest_earned += yr_interest
        balance += yr_interest
        if yr in (1, 5, 7, 10, 15, 20, 25):
            yearly.append({"year": yr, "balance": round(balance), "interest": round(yr_interest)})

    return {
        "annual_deposit": round(annual_deposit),
        "rate": current_rate,
        "years": years,
        "total_invested": round(total_invested),
        "total_interest": round(interest_earned),
        "maturity_value": round(balance),
        "tax_benefit_80c": f"₹{min(annual_deposit, 150000):,.0f}/yr",
        "tax_status": "EEE (exempt at investment, growth, and withdrawal)",
        "milestones": yearly,
    }


def fd_calculator(principal: float, annual_rate: float, years: int,
                  tax_slab: float = 30.0) -> dict:
    """Fixed Deposit calculator with TDS and post-tax return.

    TDS: 10% if interest > ₹40K/yr (₹50K for seniors). Actual tax at slab rate.
    """
    gross_amount = principal * (1 + annual_rate / 100) ** years
    gross_interest = gross_amount - principal
    annual_interest = gross_interest / years if years > 0 else 0

    # TDS applies if annual interest > ₹40K
    tds_applicable = annual_interest > 40000
    tds_rate = 0.10 if tds_applicable else 0
    tds_per_year = annual_interest * tds_rate

    # Actual tax at slab rate
    tax_on_interest = gross_interest * tax_slab / 100
    post_tax_return = gross_interest - tax_on_interest
    effective_post_tax_rate = ((principal + post_tax_return) / principal) ** (1 / years) - 1 if years > 0 else 0
    real_return = effective_post_tax_rate * 100 - 6  # assuming 6% inflation

    return {
        "principal": round(principal),
        "rate": annual_rate,
        "years": years,
        "maturity_value": round(gross_amount),
        "gross_interest": round(gross_interest),
        "tax_slab": tax_slab,
        "tax_on_interest": round(tax_on_interest),
        "post_tax_return": round(post_tax_return),
        "effective_post_tax_rate": round(effective_post_tax_rate * 100, 2),
        "real_return_after_inflation": round(real_return, 2),
        "tds_applicable": tds_applicable,
        "tds_per_year": round(tds_per_year),
        "verdict": "Negative real return" if real_return < 0 else "Positive real return",
    }


def education_loan_calc(loan_amount: float, annual_rate: float,
                        tenure_years: int, moratorium_years: int = 1) -> dict:
    """Education loan with moratorium period and Section 80E benefit.

    80E: Interest deduction for 8 years from start of repayment (no cap).
    Moratorium: typically 1 year (course duration + 6 months).
    """
    r = annual_rate / 100 / 12

    # During moratorium, interest accrues (simple interest on most loans)
    moratorium_interest = loan_amount * annual_rate / 100 * moratorium_years
    effective_principal = loan_amount + moratorium_interest

    # EMI on effective principal
    n = tenure_years * 12
    if r > 0:
        emi = effective_principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    else:
        emi = effective_principal / n

    total_payment = emi * n + 0  # moratorium interest already in principal
    total_interest = moratorium_interest + (emi * n - effective_principal)

    # 80E benefit: interest deduction for 8 years
    annual_interest_approx = total_interest / (tenure_years + moratorium_years)
    years_80e = min(8, tenure_years)
    tax_deduction_80e = annual_interest_approx * years_80e
    tax_saved_80e = tax_deduction_80e * 0.312  # 30% + cess

    return {
        "loan_amount": round(loan_amount),
        "rate": annual_rate,
        "tenure_years": tenure_years,
        "moratorium_years": moratorium_years,
        "moratorium_interest": round(moratorium_interest),
        "effective_principal": round(effective_principal),
        "emi": round(emi),
        "total_payment": round(total_payment),
        "total_interest": round(total_interest),
        "section_80e_deduction_total": round(tax_deduction_80e),
        "estimated_tax_saved_80e": round(tax_saved_80e),
        "effective_cost_after_tax": round(total_interest - tax_saved_80e),
    }


def inflation_goal_planner(current_cost: float, years: int,
                           inflation_rate: float = 6.0) -> dict:
    """Calculate future cost of a goal accounting for inflation.

    Common goals: child education, wedding, house, car, vacation.
    """
    future_cost = current_cost * (1 + inflation_rate / 100) ** years

    # SIP needed at various return rates
    sip_scenarios = {}
    for ret in [10, 12, 14]:
        r = ret / 100 / 12
        n = years * 12
        if r > 0:
            sip = future_cost * r / (((1 + r) ** n - 1) * (1 + r))
        else:
            sip = future_cost / n
        sip_scenarios[f"sip_at_{ret}pct"] = round(sip)

    return {
        "current_cost": round(current_cost),
        "years": years,
        "inflation_rate": inflation_rate,
        "future_cost": round(future_cost),
        "inflation_impact": round(future_cost - current_cost),
        "cost_multiplier": round(future_cost / current_cost, 2),
        "sip_needed": sip_scenarios,
    }


def salary_hike_impact(current_ctc: float, hike_pcts: list = None) -> dict:
    """Show how salary hikes change take-home across multiple hike scenarios."""
    if hike_pcts is None:
        hike_pcts = [10, 15, 20, 30]

    base = ctc_to_take_home(current_ctc)
    scenarios = []

    for pct in hike_pcts:
        new_ctc = current_ctc * (1 + pct / 100)
        result = ctc_to_take_home(new_ctc)
        take_home_increase = result["take_home_monthly_new"] - base["take_home_monthly_new"]
        scenarios.append({
            "hike_pct": pct,
            "new_ctc": round(new_ctc),
            "new_monthly_takehome": result["take_home_monthly_new"],
            "takehome_increase": round(take_home_increase),
            "effective_hike_pct": round(take_home_increase / base["take_home_monthly_new"] * 100, 1),
            "new_tax": result["tax_new_regime"],
        })

    return {
        "current_ctc": round(current_ctc),
        "current_monthly_takehome": base["take_home_monthly_new"],
        "current_tax": base["tax_new_regime"],
        "scenarios": scenarios,
        "insight": "Effective take-home hike is always less than CTC hike due to progressive tax slabs",
    }


def lumpsum_vs_sip(total_amount: float, annual_rate: float,
                   years: int) -> dict:
    """Compare lumpsum investment vs deploying same amount via monthly SIP."""
    # Lumpsum
    lump_value = total_amount * (1 + annual_rate / 100) ** years

    # SIP: spread total_amount over years*12 months
    monthly_sip = total_amount / (years * 12)
    r = annual_rate / 100 / 12
    n = years * 12
    sip_value = monthly_sip * (((1 + r) ** n - 1) / r) * (1 + r) if r > 0 else total_amount

    return {
        "total_amount": round(total_amount),
        "annual_rate": annual_rate,
        "years": years,
        "lumpsum_value": round(lump_value),
        "lumpsum_return": round(lump_value - total_amount),
        "sip_monthly": round(monthly_sip),
        "sip_value": round(sip_value),
        "sip_return": round(sip_value - total_amount),
        "lumpsum_advantage": round(lump_value - sip_value),
        "verdict": "Lumpsum wins in rising markets; SIP wins in volatile/falling markets via rupee cost averaging",
    }


def fire_calculator(monthly_expenses: float, current_savings: float = 0,
                    monthly_savings: float = 0, expected_return: float = 12.0,
                    withdrawal_rate: float = 3.5, inflation: float = 6.0) -> dict:
    """Financial Independence / Retire Early (FIRE) calculator.

    FIRE corpus = Annual expenses / Safe Withdrawal Rate
    """
    annual_expenses = monthly_expenses * 12
    fire_corpus = annual_expenses / (withdrawal_rate / 100)

    # Years to FIRE
    gap = fire_corpus - current_savings
    if gap <= 0:
        years_to_fire = 0
    elif monthly_savings <= 0:
        years_to_fire = -1  # Can't reach FIRE
    else:
        r = expected_return / 100 / 12
        # How many months for current_savings + SIP to reach corpus
        import math
        if r > 0:
            # FV = PV*(1+r)^n + PMT*((1+r)^n - 1)/r
            # Solve for n: iterative
            n = 0
            value = current_savings
            while value < fire_corpus and n < 600:  # max 50 years
                value = value * (1 + r) + monthly_savings
                n += 1
            years_to_fire = round(n / 12, 1)
        else:
            years_to_fire = round(gap / (monthly_savings * 12), 1)

    # FIRE variants
    lean_fire = (monthly_expenses * 0.6 * 12) / (withdrawal_rate / 100)
    fat_fire = (monthly_expenses * 1.5 * 12) / (withdrawal_rate / 100)

    return {
        "monthly_expenses": round(monthly_expenses),
        "annual_expenses": round(annual_expenses),
        "withdrawal_rate": withdrawal_rate,
        "fire_corpus_needed": round(fire_corpus),
        "current_savings": round(current_savings),
        "monthly_savings": round(monthly_savings),
        "gap": round(max(0, gap)),
        "years_to_fire": years_to_fire,
        "lean_fire_corpus": round(lean_fire),
        "regular_fire_corpus": round(fire_corpus),
        "fat_fire_corpus": round(fat_fire),
        "post_fire_monthly_income": round(fire_corpus * withdrawal_rate / 100 / 12),
    }


# ─────────────────────────────────────────────────────────────────
# Portfolio & Investment Analytics (Sharpe, Sortino, Drawdown, etc.)
# ─────────────────────────────────────────────────────────────────

def sharpe_ratio(returns: list, risk_free_rate: float = 6.0) -> dict:
    """Calculate annualized Sharpe Ratio from monthly/daily returns.
    returns: list of periodic returns as decimals (e.g., 0.02 = 2%)
    risk_free_rate: annual risk-free rate as percentage (default 6% for India)
    """
    if not returns or len(returns) < 2:
        return {"error": "Need at least 2 return periods"}
    arr = np.array(returns, dtype=float)
    periods = len(arr)
    # Assume monthly if <=60 periods, daily otherwise
    ann_factor = 12 if periods <= 60 else 252
    rf_per_period = (1 + risk_free_rate / 100) ** (1 / ann_factor) - 1

    excess = arr - rf_per_period
    mean_excess = float(np.mean(excess))
    std = float(np.std(excess, ddof=1))
    if std == 0:
        return {"error": "Zero volatility — cannot compute Sharpe"}

    sharpe = (mean_excess / std) * np.sqrt(ann_factor)
    quality = ("Excellent" if sharpe > 1.5 else "Good" if sharpe > 1.0
               else "Acceptable" if sharpe > 0.5 else "Poor")
    return {
        "sharpe_ratio": round(float(sharpe), 3),
        "annualized_return_pct": round(float(np.mean(arr) * ann_factor * 100), 2),
        "annualized_volatility_pct": round(float(std * np.sqrt(ann_factor) * 100), 2),
        "risk_free_rate": risk_free_rate,
        "quality": quality,
    }


def sortino_ratio(returns: list, risk_free_rate: float = 6.0) -> dict:
    """Calculate annualized Sortino Ratio (penalizes only downside volatility).
    More relevant than Sharpe for investors who care about losses, not upside swings.
    """
    if not returns or len(returns) < 2:
        return {"error": "Need at least 2 return periods"}
    arr = np.array(returns, dtype=float)
    periods = len(arr)
    ann_factor = 12 if periods <= 60 else 252
    rf_per_period = (1 + risk_free_rate / 100) ** (1 / ann_factor) - 1

    excess = arr - rf_per_period
    downside = excess[excess < 0]
    if len(downside) == 0:
        return {
            "sortino_ratio": float("inf"),
            "annualized_return_pct": round(float(np.mean(arr) * ann_factor * 100), 2),
            "downside_risk_pct": 0.0,
            "quality": "No negative periods",
        }

    downside_std = float(np.sqrt(np.mean(downside ** 2)))
    sortino = (float(np.mean(excess)) / downside_std) * np.sqrt(ann_factor)
    quality = ("Excellent" if sortino > 2 else "Good" if sortino > 1
               else "Acceptable" if sortino > 0 else "Poor")
    return {
        "sortino_ratio": round(float(sortino), 3),
        "annualized_return_pct": round(float(np.mean(arr) * ann_factor * 100), 2),
        "downside_risk_pct": round(float(downside_std * np.sqrt(ann_factor) * 100), 2),
        "quality": quality,
    }


def max_drawdown(prices: list) -> dict:
    """Calculate maximum drawdown from a price series.
    prices: list of portfolio values or NAV over time
    """
    if not prices or len(prices) < 2:
        return {"error": "Need at least 2 price points"}
    arr = np.array(prices, dtype=float)
    peak = np.maximum.accumulate(arr)
    drawdowns = (arr - peak) / peak
    mdd = float(np.min(drawdowns))
    mdd_end_idx = int(np.argmin(drawdowns))
    mdd_start_idx = int(np.argmax(arr[:mdd_end_idx + 1]))

    # Recovery: find first point after trough that exceeds previous peak
    recovery_idx = None
    trough_value = arr[mdd_end_idx]
    peak_value = arr[mdd_start_idx]
    for i in range(mdd_end_idx, len(arr)):
        if arr[i] >= peak_value:
            recovery_idx = i
            break

    return {
        "max_drawdown_pct": round(mdd * 100, 2),
        "peak_index": mdd_start_idx,
        "trough_index": mdd_end_idx,
        "peak_value": round(float(arr[mdd_start_idx]), 2),
        "trough_value": round(float(arr[mdd_end_idx]), 2),
        "recovered": recovery_idx is not None,
        "recovery_index": recovery_idx,
        "severity": ("Mild (<10%)" if abs(mdd) < 0.10 else
                     "Moderate (10-20%)" if abs(mdd) < 0.20 else
                     "Severe (20-30%)" if abs(mdd) < 0.30 else
                     "Crash (>30%)"),
    }


def rolling_returns(prices: list, window: int = 12) -> dict:
    """Calculate rolling returns over a window (months/days).
    Useful for checking consistency of mutual fund performance.
    """
    if not prices or len(prices) <= window:
        return {"error": f"Need more than {window} price points"}
    arr = np.array(prices, dtype=float)
    rolls = []
    for i in range(window, len(arr)):
        ret = (arr[i] / arr[i - window]) - 1
        rolls.append(float(ret))

    rolls_arr = np.array(rolls)
    return {
        "window": window,
        "num_periods": len(rolls),
        "mean_return_pct": round(float(np.mean(rolls_arr) * 100), 2),
        "median_return_pct": round(float(np.median(rolls_arr) * 100), 2),
        "best_return_pct": round(float(np.max(rolls_arr) * 100), 2),
        "worst_return_pct": round(float(np.min(rolls_arr) * 100), 2),
        "std_return_pct": round(float(np.std(rolls_arr) * 100), 2),
        "pct_positive": round(float(np.mean(rolls_arr > 0) * 100), 1),
    }


def future_value(present_value: float = 0, payment: float = 0,
                 rate: float = 12.0, periods: int = 120) -> dict:
    """Calculate future value using numpy-financial (handles PV + PMT).
    rate: annual rate as percentage
    periods: total number of months
    payment: monthly payment (negative = outflow)
    """
    monthly_rate = rate / 100 / 12
    fv = float(npf.fv(monthly_rate, periods, -payment, -present_value))
    total_invested = present_value + payment * periods
    return {
        "future_value": round(fv, 2),
        "present_value": round(present_value, 2),
        "monthly_payment": round(payment, 2),
        "annual_rate": rate,
        "months": periods,
        "total_invested": round(total_invested, 2),
        "total_return": round(fv - total_invested, 2),
    }


def present_value(future_amount: float, rate: float = 12.0,
                  periods: int = 120, payment: float = 0) -> dict:
    """Calculate present value needed using numpy-financial.
    Answers: 'How much do I need today to have ₹X in N months at Y% rate?'
    """
    monthly_rate = rate / 100 / 12
    pv = float(npf.pv(monthly_rate, periods, -payment, -future_amount))
    return {
        "present_value": round(pv, 2),
        "future_amount": round(future_amount, 2),
        "annual_rate": rate,
        "months": periods,
        "monthly_payment": round(payment, 2),
    }


def payment_required(future_amount: float = 0, present_value_amt: float = 0,
                     rate: float = 12.0, periods: int = 120) -> dict:
    """Calculate monthly payment needed using numpy-financial.
    Answers: 'How much SIP do I need monthly to reach ₹X in N months?'
    """
    monthly_rate = rate / 100 / 12
    pmt = float(npf.pmt(monthly_rate, periods, -present_value_amt, -future_amount))
    return {
        "monthly_payment": round(pmt, 2),
        "future_amount": round(future_amount, 2),
        "present_investment": round(present_value_amt, 2),
        "annual_rate": rate,
        "months": periods,
        "total_paid": round(pmt * periods + present_value_amt, 2),
    }
