"""Financial calculation tools."""
from __future__ import annotations

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
    """Enhanced SIP calculator with delay cost, milestones, and CAGR.
    Uses geometric monthly rate: (1+r)^(1/12)-1 — matches Groww.
    Features: year-wise milestones, delay penalty, wealth ratio."""
    r = (1 + annual_rate / 100) ** (1/12) - 1  # Geometric monthly rate
    n = years * 12  # Total months
    if r == 0:
        future_value = monthly_investment * n
    else:
        future_value = monthly_investment * (((1 + r) ** n - 1) / r) * (1 + r)
    total_invested = monthly_investment * n
    wealth_gained = future_value - total_invested

    # Delay cost: what you lose by waiting 1, 3, 5 years
    delay_costs = {}
    for delay in [1, 3, 5]:
        if years - delay > 0:
            nd = (years - delay) * 12
            fv_d = monthly_investment * (((1 + r) ** nd - 1) / r) * (1 + r) if r > 0 else monthly_investment * nd
            delay_costs[f"delay_{delay}yr_loss"] = round(future_value - fv_d)

    # Year-wise milestones
    milestones = []
    for yr in [1, 3, 5, 10, 15, 20, 25, 30]:
        if yr <= years:
            nm = yr * 12
            fv_m = monthly_investment * (((1 + r) ** nm - 1) / r) * (1 + r) if r > 0 else monthly_investment * nm
            inv_m = monthly_investment * nm
            milestones.append({"year": yr, "invested": round(inv_m), "value": round(fv_m), "gain": round(fv_m - inv_m)})

    # Wealth multiplier
    wealth_multiplier = round(future_value / total_invested, 2) if total_invested > 0 else 0

    return {
        "monthly_investment": round(monthly_investment, 2),
        "annual_rate": annual_rate,
        "years": years,
        "total_invested": round(total_invested, 2),
        "future_value": round(future_value, 2),
        "wealth_gained": round(wealth_gained, 2),
        "absolute_return_pct": round((wealth_gained / total_invested) * 100, 2),
        "wealth_multiplier": wealth_multiplier,
        **delay_costs,
        "milestones": milestones,
    }


def emi_calculator(principal: float, annual_rate: float,
                   tenure_months: int) -> dict:
    """Enhanced EMI calculator with amortization summary, processing fee impact, and total cost breakdown."""
    r = annual_rate / 100 / 12
    if r == 0:
        emi = principal / tenure_months
    else:
        emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    # Year-wise principal vs interest breakdown (first few years)
    balance = principal
    yearly_breakup = []
    for yr in range(1, min(int(tenure_months / 12) + 2, 31)):
        yr_principal = 0
        yr_interest = 0
        for _ in range(12):
            if balance <= 0:
                break
            interest_part = balance * r
            principal_part = min(emi - interest_part, balance)
            yr_principal += principal_part
            yr_interest += interest_part
            balance -= principal_part
        if yr_principal > 0:
            yearly_breakup.append({"year": yr, "principal_paid": round(yr_principal), "interest_paid": round(yr_interest), "balance": round(max(0, balance))})

    # Processing fee impact (typical 1-2%)
    processing_fee_est = round(principal * 0.01)
    effective_cost = total_interest + processing_fee_est

    # Affordability check (EMI should be <40% of income)
    min_income_needed = round(emi / 0.40)

    return {
        "principal": round(principal, 2),
        "annual_rate": annual_rate,
        "tenure_months": tenure_months,
        "tenure_years": round(tenure_months / 12, 1),
        "emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "interest_to_principal_ratio": round(total_interest / principal * 100, 2),
        "processing_fee_est": processing_fee_est,
        "effective_cost_with_fees": round(effective_cost),
        "min_monthly_income_needed": min_income_needed,
        "first_month_interest": round(principal * r) if r > 0 else 0,
        "first_month_principal": round(emi - principal * r) if r > 0 else round(emi),
        "yearly_breakup": yearly_breakup[:5],
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

    # Emergency buffer: 6–12 months of future expenses
    emergency_6mo = future_expense * 6
    emergency_12mo = future_expense * 12
    total_corpus_with_emergency = corpus + emergency_6mo

    # Step-up SIP: if you increase SIP by 10% annually, how much less you need to start with
    stepup_pct = 10
    stepup_corpus = 0
    stepup_sip_start = monthly_sip  # start from flat SIP and reduce
    # Binary search for starting SIP with 10% annual stepup
    lo, hi = 0, monthly_sip
    for _ in range(50):
        mid = (lo + hi) / 2
        val = 0
        for yr in range(int(years_to_retire)):
            current = mid * (1 + stepup_pct / 100) ** yr
            for _ in range(12):
                val = (val + current) * (1 + monthly_rate)
        if val >= corpus:
            hi = mid
        else:
            lo = mid
    stepup_sip_start = round(hi)
    stepup_saving = round(monthly_sip - hi)

    # Wealth multiplier
    total_sip_invested = monthly_sip * n
    wealth_multiplier = round(corpus / total_sip_invested, 2) if total_sip_invested > 0 else 0

    return {
        "current_monthly_expense": round(monthly_expense, 2),
        "future_monthly_expense": round(future_expense, 2),
        "future_annual_expense": round(annual_expense, 2),
        "corpus_needed": round(corpus, 2),
        "monthly_sip_needed": round(monthly_sip, 2),
        "lumpsum_needed_today": round(corpus / (1 + expected_return / 100) ** years_to_retire),
        "years_to_retire": years_to_retire,
        "years_in_retirement": years_in_retirement,
        "total_sip_invested": round(total_sip_invested),
        "wealth_from_compounding": round(corpus - total_sip_invested),
        "wealth_multiplier": wealth_multiplier,
        "expense_inflation_multiplier": round(future_expense / monthly_expense, 2),
        "emergency_fund_6mo": round(emergency_6mo),
        "emergency_fund_12mo": round(emergency_12mo),
        "total_corpus_with_emergency": round(total_corpus_with_emergency),
        "stepup_sip_start_10pct": stepup_sip_start,
        "stepup_sip_saving": stepup_saving,
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
                     nps_employer_pct: float = 0,
                     bonus_in_ctc: float = 0,
                     is_metro: bool = True,
                     monthly_rent: float = 0,
                     lta_annual: float = 0,
                     food_coupons_monthly: float = 0,
                     monthly_additional_deduction: float = 0,
                     medical_insurance_employer: float = 0,
                     section_80d_self: float = 0) -> dict:
    """Given annual CTC, compute detailed salary breakdown and take-home.

    Covers: Basic, HRA (with exemption), Special Allowance, EPF (with EPS split
    + wage ceiling), Gratuity provision, Professional Tax, LTA, Food Coupons,
    NPS, Medical Insurance, Income Tax (both regimes with proper deductions).

    Enhanced inputs inspired by Groww, AmbitionBox, ClearTax, and SalaryBox:
    - Bonus included in CTC (deducted to get gross)
    - Metro/non-metro HRA rates and exemption
    - Actual rent for HRA exemption computation
    - LTA annual allowance (exempt up to travel proof)
    - Food coupons/meal vouchers (exempt up to ₹26,400/yr per CBDT)
    - Additional monthly deductions (insurance, loans, etc.)
    - Section 80D self health insurance (₹25K limit)
    - Employer medical insurance (exemption under 17(2))

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
        nps_employer_pct: Employer NPS contribution as % of basic (0-14%)
        bonus_in_ctc: Annual bonus/variable pay included in CTC (deducted from gross)
        is_metro: True for metro cities (HRA=50% of Basic), False for non-metro (40%)
        monthly_rent: Monthly rent paid (for HRA exemption calculation)
        lta_annual: Annual LTA component (exempt with proof, up to ₹20K typically)
        food_coupons_monthly: Monthly food/meal vouchers (exempt up to ₹2,200/mo)
        monthly_additional_deduction: Other monthly deductions (insurance, etc.)
        medical_insurance_employer: Annual employer medical insurance premium (tax exempt)
        section_80d_self: Health insurance premium (self) for 80D deduction (max ₹25K)
    """
    basic = ctc_annual * basic_pct
    basic_monthly = basic / 12
    hra_pct = 0.50 if is_metro else 0.40  # Metro: 50%, Non-metro: 40%
    hra = basic * hra_pct

    # ── Bonus / Variable Pay ──
    bonus = max(0, bonus_in_ctc)

    # ── LTA (Leave Travel Allowance) ──
    # Exempt if travel bills submitted; otherwise taxable
    lta = max(0, lta_annual)

    # ── Food Coupons / Meal Vouchers ──
    # Exempt up to ₹2,200/month = ₹26,400/yr as per CBDT
    FOOD_COUPON_EXEMPT_MONTHLY = 2200
    food_monthly = max(0, food_coupons_monthly)
    food_annual = food_monthly * 12
    food_exempt = min(food_annual, FOOD_COUPON_EXEMPT_MONTHLY * 12)  # ₹26,400 max
    food_taxable = max(0, food_annual - food_exempt)

    # ── EPF Contributions ──
    EPF_WAGE_CEILING_MONTHLY = 15000
    epf_wage_ceiling_annual = EPF_WAGE_CEILING_MONTHLY * 12

    if epf_on_full_basic:
        epf_basic = basic
    else:
        epf_basic = min(basic, epf_wage_ceiling_annual)

    epf_employee = epf_basic * 0.12
    epf_employer_total = epf_basic * 0.12

    # EPS: 8.33% of Basic, ALWAYS capped at ₹15,000/mo
    eps_basic_capped = min(basic, epf_wage_ceiling_annual)
    eps_contribution = eps_basic_capped * 0.0833
    epf_employer_to_epf = epf_employer_total - eps_contribution

    # EDLI: 0.50% of Basic (capped at ₹15K/mo)
    edli = min(basic, epf_wage_ceiling_annual) * 0.005

    # ── NPS (if applicable) ──
    nps_employer = basic * (nps_employer_pct / 100) if nps_employer_pct else 0

    # ── Gratuity Provision ──
    gratuity_annual = (basic_monthly * 15) / 26
    gratuity_5yr = (basic_monthly * 15 * 5) / 26
    gratuity_10yr = (basic_monthly * 15 * 10) / 26
    gratuity_20yr = (basic_monthly * 15 * 20) / 26
    GRATUITY_TAX_EXEMPT_LIMIT = 2000000

    # ── Employer Medical Insurance ──
    medical_ins_employer = max(0, medical_insurance_employer)

    # ── Special Allowance ──
    # CTC = Basic + HRA + EPF_er + EDLI + Gratuity + NPS_er + Bonus + LTA + Food + Medical + Special
    special_allowance = (ctc_annual - basic - hra - epf_employer_total
                         - edli - gratuity_annual - nps_employer
                         - bonus - lta - food_annual - medical_ins_employer)

    # ── Gross Salary ──
    # Gross = CTC minus employer-only costs
    employer_costs = epf_employer_total + edli + gratuity_annual + nps_employer + medical_ins_employer
    gross_salary = ctc_annual - employer_costs

    # ── Professional Tax ──
    professional_tax = 2400

    # ── Additional Deductions ──
    additional_deduction_annual = monthly_additional_deduction * 12

    # ── HRA Exemption (Old Regime only) ──
    # Least of: (a) Actual HRA, (b) Rent - 10% Basic, (c) 50%/40% of Basic
    rent_annual = monthly_rent * 12
    if rent_annual > 0:
        hra_exempt = min(
            hra,                                        # (a) Actual HRA received
            max(0, rent_annual - 0.10 * basic),         # (b) Rent paid - 10% Basic
            basic * hra_pct                              # (c) 50%/40% of Basic
        )
    else:
        hra_exempt = 0  # No rent = HRA fully taxable

    # ── Income Tax (New Regime) ──
    # New regime: Standard deduction ₹75,000 only, no 80C/80D/HRA deductions
    new_regime_deduction = nps_employer
    new_taxable = gross_salary - new_regime_deduction
    new_tax = tax_bracket_india(new_taxable, "new")

    # ── Income Tax (Old Regime) ──
    # Old regime: Std deduction ₹50K + 80C (₹1.5L) + HRA exempt + LTA + 80D + 80CCD(2)
    section_80c_total = min(epf_employee + additional_80c, 150000)
    section_80d_total = min(section_80d_self, 25000)  # Self: ₹25K limit (non-senior)
    section_80ccd2_nps = nps_employer
    old_regime_deduction = (section_80c_total + section_80ccd2_nps
                            + hra_exempt + lta + food_exempt
                            + section_80d_total)
    old_taxable = gross_salary - old_regime_deduction
    old_tax = tax_bracket_india(old_taxable, "old")

    # ── Take-Home ──
    total_employee_deductions_new = epf_employee + professional_tax + new_tax["total_tax"] + additional_deduction_annual
    total_employee_deductions_old = epf_employee + professional_tax + old_tax["total_tax"] + additional_deduction_annual
    take_home_new = gross_salary - total_employee_deductions_new
    take_home_old = gross_salary - total_employee_deductions_old

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
        "hra_pct": round(hra_pct * 100),
        "city_type": "Metro" if is_metro else "Non-Metro",
        "special_allowance": round(max(0, special_allowance)),
        "special_allowance_monthly": monthly_special,

        # Bonus / Variable Pay
        "bonus_annual": round(bonus),
        "bonus_monthly": round(bonus / 12) if bonus > 0 else 0,

        # LTA
        "lta_annual": round(lta),

        # Food Coupons
        "food_coupons_annual": round(food_annual),
        "food_coupons_exempt": round(food_exempt),
        "food_coupons_taxable": round(food_taxable),

        # EPF details
        "epf_on_full_basic": epf_on_full_basic,
        "epf_basic": round(epf_basic),
        "epf_wage_ceiling": epf_wage_ceiling_annual,
        "epf_employee": round(epf_employee),
        "epf_employee_monthly": monthly_epf_employee,
        "epf_employer_total": round(epf_employer_total),
        "epf_employer_monthly": monthly_epf_employer,
        "epf_employer_epf": round(epf_employer_to_epf),
        "eps_contribution": round(eps_contribution),
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

        # Medical Insurance (Employer)
        "medical_insurance_employer": round(medical_ins_employer),

        # Gross & Tax
        "gross_salary": round(gross_salary),
        "gross_monthly": monthly_gross,
        "professional_tax": professional_tax,
        "professional_tax_monthly": monthly_professional_tax,

        # Additional deductions
        "additional_deduction_annual": round(additional_deduction_annual),
        "additional_deduction_monthly": round(monthly_additional_deduction),

        # HRA Exemption (Old Regime)
        "rent_annual": round(rent_annual),
        "rent_monthly": round(monthly_rent),
        "hra_exempt": round(hra_exempt),

        # Old regime deductions
        "section_80c_auto_epf": round(min(epf_employee, 150000)),
        "section_80c_total": round(section_80c_total),
        "section_80c_remaining": round(max(0, 150000 - epf_employee)),
        "section_80d_self": round(section_80d_total),
        "old_regime_total_deductions": round(old_regime_deduction),

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

        # Regime comparison
        "better_regime": "New Regime" if take_home_new >= take_home_old else "Old Regime",
        "regime_savings": round(abs(take_home_new - take_home_old)),

        # Retirement accrual
        "total_retirement_annual": round(total_retirement_annual),
        "total_retirement_monthly": round(total_retirement_annual / 12),

        # Total employee deductions per month (EPF + PT + Tax + Additional)
        "total_deductions_monthly_new": round(total_employee_deductions_new / 12),
        "total_deductions_monthly_old": round(total_employee_deductions_old / 12),

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
        "annual_tax_saving_approx": round(exemption * 0.312),
        "monthly_tax_saving": round(exemption * 0.312 / 12),
        "optimal_rent": round(basic_annual * 0.10 + basic_annual * pct),
        "exemption_rule": "Actual HRA" if exemption == option1 else ("Rent - 10% Basic" if exemption == option2 else f"{int(pct*100)}% of Basic"),
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
    new_total_interest = total_new - principal
    new_total_tenure = prepay_after_months + (new_tenure if reduce == "tenure" else (tenure_months - prepay_after_months))

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
        "new_total_tenure": new_total_tenure,
        "new_total_interest": round(max(0, new_total_interest)),
        "months_saved": months_saved if reduce == "tenure" else 0,
        "years_saved": round(months_saved / 12, 1) if reduce == "tenure" else 0,
        "total_new_cost": round(total_new),
        "interest_saved": round(max(0, interest_saved)),
        "interest_saved_pct": round(interest_saved / (total_original - principal) * 100, 1) if (total_original - principal) > 0 else 0,
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

    # Holding period optimization
    if at in ("equity", "equity_mf") and holding_period_months < 12:
        ltcg_tax_if_held = max(0, gain - 125000) * 0.125 * 1.04
        potential_saving = total_tax - ltcg_tax_if_held
        hold_suggestion = f"Hold {12 - holding_period_months} more months to save ₹{potential_saving:,.0f}" if potential_saving > 0 else "Already LTCG eligible"
    elif at in ("gold", "property") and holding_period_months < 24:
        ltcg_tax_if_held = gain * 0.125 * 1.04
        potential_saving = total_tax - ltcg_tax_if_held
        hold_suggestion = f"Hold {24 - holding_period_months} more months to save ₹{potential_saving:,.0f}" if potential_saving > 0 else "Already LTCG eligible"
    else:
        hold_suggestion = "Optimal holding period reached"

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
        "in_hand_pct": round((gain - total_tax) / gain * 100, 1) if gain > 0 else 0,
        "asset_type": asset_type,
        "type": tax_type,
        "holding_tip": hold_suggestion,
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

    wealth_multiplier = round(balance / total_invested, 2) if total_invested > 0 else 0

    # Compare with taxable FD at same rate
    fd_gross = total_invested * (1 + current_rate / 100) ** years  # simplified
    fd_post_tax = total_invested + (fd_gross - total_invested) * 0.7  # 30% tax
    ppf_advantage = round(balance - fd_post_tax)

    # Partial withdrawal: from 7th year, max 50% of balance at end of 4th preceding year
    partial_withdrawal_year = 7

    # Loan facility: 3rd to 6th year, max 25% of balance
    loan_available_year = 3

    return {
        "annual_deposit": round(annual_deposit),
        "rate": current_rate,
        "years": years,
        "total_invested": round(total_invested),
        "total_interest": round(interest_earned),
        "maturity_value": round(balance),
        "wealth_multiplier": wealth_multiplier,
        "tax_benefit_80c": min(round(annual_deposit), 150000),
        "tax_status": "EEE (exempt at investment, growth, and withdrawal)",
        "ppf_advantage_over_fd": ppf_advantage,
        "partial_withdrawal_from_year": partial_withdrawal_year,
        "loan_available_year": loan_available_year,
        "monthly_deposit_equivalent": round(annual_deposit / 12),
        "milestones": yearly,
    }


def fd_calculator(principal: float, annual_rate: float, years: int,
                  compounding: int = 4, tax_slab: float = 30.0) -> dict:
    """Fixed Deposit calculator with TDS and post-tax return.
    Compounding: 1=annual, 4=quarterly (standard), 12=monthly.
    Formula: A = P × (1 + r/n)^(n×t)  — cross-referenced with Groww.
    TDS: 10% if interest > ₹40K/yr (₹50K for seniors). Actual tax at slab rate.
    """
    n = compounding  # compounding frequency per year
    gross_amount = principal * (1 + annual_rate / 100 / n) ** (n * years)
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

    # Compounding comparison
    annual_amount = principal * (1 + annual_rate / 100) ** years
    quarterly_amount = principal * (1 + annual_rate / 100 / 4) ** (4 * years)
    monthly_amount = principal * (1 + annual_rate / 100 / 12) ** (12 * years)
    compounding_benefit = round(gross_amount - annual_amount) if n > 1 else 0

    # Annual interest for TDS planning
    annual_interest_approx = round(gross_interest / years) if years > 0 else 0

    return {
        "principal": round(principal),
        "rate": annual_rate,
        "years": years,
        "compounding": "Quarterly" if n == 4 else ("Monthly" if n == 12 else "Annually"),
        "maturity_value": round(gross_amount),
        "gross_interest": round(gross_interest),
        "annual_interest_approx": annual_interest_approx,
        "tax_slab": tax_slab,
        "tax_on_interest": round(tax_on_interest),
        "post_tax_return": round(post_tax_return),
        "post_tax_maturity": round(principal + post_tax_return),
        "effective_post_tax_rate": round(effective_post_tax_rate * 100, 2),
        "real_return_after_inflation": round(real_return, 2),
        "tds_applicable": tds_applicable,
        "tds_per_year": round(tds_per_year),
        "compounding_benefit": compounding_benefit,
        "verdict": "Negative real return — consider equity/PPF" if real_return < 0 else "Positive real return",
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

    # Effective interest rate after tax benefit
    effective_interest_cost = total_interest - tax_saved_80e
    effective_rate_post_tax = (effective_interest_cost / loan_amount) / (tenure_years + moratorium_years) * 100 if loan_amount > 0 else 0

    # Part-time income needed to cover EMI
    min_income_for_emi = round(emi / 0.30)  # EMI should be <30% of income

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
        "effective_rate_after_tax": round(effective_rate_post_tax, 2),
        "total_cost_with_moratorium": round(total_payment + moratorium_interest),
        "emi_to_loan_ratio": round(emi / loan_amount * 100, 2),
        "min_income_for_emi": min_income_for_emi,
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
        "sip_at_10pct": sip_scenarios.get("sip_at_10pct", 0),
        "sip_at_12pct": sip_scenarios.get("sip_at_12pct", 0),
        "sip_at_14pct": sip_scenarios.get("sip_at_14pct", 0),
        "lumpsum_needed_today": round(future_cost / (1.12 ** years)),
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

    result = {
        "current_ctc": round(current_ctc),
        "current_monthly_takehome": base["take_home_monthly_new"],
        "current_tax": base["tax_new_regime"],
        "scenarios": scenarios,
        "insight": "Effective take-home hike is always less than CTC hike due to progressive tax slabs",
    }
    # Flatten top scenarios into result for UI display
    for s in scenarios[:4]:
        pct = s["hike_pct"]
        result[f"hike_{pct}pct_new_ctc"] = s["new_ctc"]
        result[f"hike_{pct}pct_takehome"] = s["new_monthly_takehome"]
        result[f"hike_{pct}pct_increase"] = s["takehome_increase"]
        result[f"hike_{pct}pct_effective"] = s["effective_hike_pct"]
    return result


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

    lump_advantage = lump_value - sip_value

    return {
        "total_amount": round(total_amount),
        "annual_rate": annual_rate,
        "years": years,
        "lumpsum_value": round(lump_value),
        "lumpsum_return": round(lump_value - total_amount),
        "lumpsum_return_pct": round((lump_value - total_amount) / total_amount * 100, 1),
        "sip_monthly": round(monthly_sip),
        "sip_value": round(sip_value),
        "sip_return": round(sip_value - total_amount),
        "sip_return_pct": round((sip_value - total_amount) / total_amount * 100, 1),
        "lumpsum_advantage": round(lump_value - sip_value),
        "verdict": "Lumpsum wins in rising markets; SIP wins in volatile/falling markets via rupee cost averaging",
    }


def fire_calculator(monthly_expenses: float, current_age: int = 30,
                    retirement_age: int = 50, current_savings: float = 0,
                    monthly_savings: float = 0, expected_return: float = 12.0,
                    inflation_rate: float = 6.0, coast_fire_age: int = 0) -> dict:
    """Enhanced FIRE calculator — 4 types of FIRE + Coast FIRE + timeline.

    Cross-referenced with: 1% Club, ET Money, Scripbox.

    Types:
    - Lean FIRE: Minimalist lifestyle, corpus = inflation-adjusted annual expenses × 25
    - Regular FIRE: Standard 4% rule, corpus = inflation-adjusted annual expenses × 25
      (1% Club uses ×25; ET Money uses ×33 for more conservative estimate)
    - Fat FIRE: Luxurious lifestyle, corpus = inflation-adjusted annual expenses × 50
    - Barista FIRE: Part-time income covers 30%, investments cover 70%,
      corpus = 70% of inflation-adjusted annual expenses × 33
    - Coast FIRE: Amount needed today so it grows to FIRE number by retirement
      (no additional investments needed after this point)
    """
    years_to_retire = retirement_age - current_age
    if years_to_retire <= 0:
        return {"error": "Retirement age must be greater than current age"}

    # ─── Current & future expenses ───
    annual_expenses_today = monthly_expenses * 12
    monthly_expenses_at_retire = monthly_expenses * (1 + inflation_rate / 100) ** years_to_retire
    annual_expenses_at_retire = monthly_expenses_at_retire * 12

    # ─── Lean FIRE: frugal lifestyle (60% of expenses × 25) ───
    lean_annual = annual_expenses_at_retire * 0.6
    lean_fire = lean_annual * 25

    # ─── Regular FIRE: 4% rule (×25) — matching 1% Club ───
    regular_fire = annual_expenses_at_retire * 25

    # ─── Fat FIRE: comfortable lifestyle (150% expenses × 50) — 1% Club/ET Money ───
    fat_fire = annual_expenses_at_retire * 50

    # ─── Barista FIRE: part-time income covers 30% (ET Money methodology) ───
    barista_fire = annual_expenses_at_retire * 0.70 * 33

    # ─── Coast FIRE: invest now to grow to FIRE number without additional savings ───
    coast_target_age = coast_fire_age if coast_fire_age > current_age else current_age + 2
    years_coast_to_retire = retirement_age - coast_target_age
    if years_coast_to_retire > 0 and expected_return > 0:
        # PV of regular_fire discounted back to coast_fire_age
        coast_fire = regular_fire / ((1 + expected_return / 100) ** years_coast_to_retire)
    else:
        coast_fire = regular_fire

    # ─── Years to reach each FIRE type (iterative SIP + growth) ───
    def years_to_reach(target):
        if current_savings >= target:
            return 0
        if monthly_savings <= 0:
            return -1  # Can't reach
        r = expected_return / 100 / 12
        n = 0
        value = current_savings
        while value < target and n < 720:  # max 60 years
            value = value * (1 + r) + monthly_savings
            n += 1
        if n >= 720:
            return -1
        return round(n / 12, 1)

    years_lean = years_to_reach(lean_fire)
    years_regular = years_to_reach(regular_fire)
    years_fat = years_to_reach(fat_fire)
    years_barista = years_to_reach(barista_fire)

    # ─── Monthly SIP needed to reach regular FIRE ───
    r_monthly = expected_return / 100 / 12
    months = years_to_retire * 12
    if r_monthly > 0 and months > 0:
        gap = regular_fire - current_savings * (1 + r_monthly) ** months
        if gap > 0:
            sip_for_fire = gap * r_monthly / ((1 + r_monthly) ** months - 1)
        else:
            sip_for_fire = 0
    else:
        sip_for_fire = (regular_fire - current_savings) / max(months, 1)

    # ─── Savings rate needed ───
    total_monthly_income_needed = monthly_expenses + sip_for_fire
    savings_rate_needed = (sip_for_fire / total_monthly_income_needed * 100) if total_monthly_income_needed > 0 else 0

    # ─── Post-FIRE monthly income (4% rule) ───
    post_fire_monthly = regular_fire * 0.04 / 12

    # ─── FIRE type recommendation ───
    if monthly_savings > 0:
        if years_lean != -1 and years_lean <= years_to_retire:
            if years_regular != -1 and years_regular <= years_to_retire:
                if years_fat != -1 and years_fat <= years_to_retire:
                    recommendation = "Fat FIRE"
                else:
                    recommendation = "Regular FIRE"
            else:
                recommendation = "Lean FIRE"
        else:
            recommendation = "Increase savings — FIRE not achievable at current rate"
    else:
        recommendation = "Start investing to begin your FIRE journey"

    return {
        "current_age": current_age,
        "retirement_age": retirement_age,
        "years_to_retire": years_to_retire,
        "monthly_expenses_today": round(monthly_expenses),
        "annual_expenses_today": round(annual_expenses_today),
        "monthly_expenses_at_retire": round(monthly_expenses_at_retire),
        "annual_expenses_at_retire": round(annual_expenses_at_retire),
        "inflation_rate": inflation_rate,
        "expected_return": expected_return,
        "lean_fire_corpus": round(lean_fire),
        "regular_fire_corpus": round(regular_fire),
        "fat_fire_corpus": round(fat_fire),
        "barista_fire_corpus": round(barista_fire),
        "coast_fire_corpus": round(coast_fire),
        "coast_fire_age": coast_target_age,
        "years_to_lean_fire": years_lean,
        "years_to_regular_fire": years_regular,
        "years_to_fat_fire": years_fat,
        "years_to_barista_fire": years_barista,
        "current_savings": round(current_savings),
        "monthly_savings": round(monthly_savings),
        "sip_needed_for_fire": round(sip_for_fire),
        "savings_rate_needed_pct": round(savings_rate_needed, 1),
        "post_fire_monthly_income": round(post_fire_monthly),
        "fire_recommendation": recommendation,
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


# ──────────────────────── Groww-style Calculators ────────────────────────

def rd_calculator(monthly_deposit: float, annual_rate: float, years: int) -> dict:
    """Recurring Deposit calculator — quarterly compounding per RBI norms."""
    r = annual_rate / 100
    n = 4  # quarterly compounding
    months = int(years * 12)
    maturity = 0.0
    for m in range(1, months + 1):
        remaining_quarters = (months - m + 1) / 3
        maturity += monthly_deposit * (1 + r / n) ** (n * remaining_quarters / n)
    # Simpler standard formula: sum of compound interest on each installment
    # Each deposit of P earns interest for (months - m) months with quarterly compounding
    maturity = 0.0
    for m in range(months):
        remaining_months = months - m
        t_years = remaining_months / 12
        amount = monthly_deposit * (1 + r / n) ** (n * t_years)
        maturity += amount
    total_invested = monthly_deposit * months
    total_interest = maturity - total_invested
    wealth_multiplier = round(maturity / total_invested, 2) if total_invested > 0 else 0

    # Compare with SIP at same rate
    r_sip = annual_rate / 100 / 12
    if r_sip > 0:
        sip_value = monthly_deposit * (((1 + r_sip) ** months - 1) / r_sip) * (1 + r_sip)
    else:
        sip_value = total_invested
    sip_advantage = round(sip_value - maturity)

    return {
        "monthly_deposit": monthly_deposit,
        "annual_rate": annual_rate,
        "years": years,
        "total_invested": round(total_invested, 2),
        "maturity_value": round(maturity, 2),
        "total_interest": round(total_interest, 2),
        "effective_yield_pct": round((maturity / total_invested - 1) * 100, 2) if total_invested > 0 else 0,
        "wealth_multiplier": wealth_multiplier,
        "monthly_interest_approx": round(total_interest / months) if months > 0 else 0,
        "sip_mf_comparison": round(sip_value),
        "sip_advantage_over_rd": sip_advantage,
    }


def ssy_calculator(annual_deposit: float, girl_age: int,
                   current_rate: float = 8.2) -> dict:
    """Sukanya Samriddhi Yojana — deposits for first 15 years, maturity 21 years from opening.
    Interest compounded annually at government-set rate.
    Cross-referenced with Groww, ClearTax, India Post SSY rules."""
    deposit_years = 15  # must deposit for first 15 years (incl. opening year)
    maturity_years = 21  # account matures 21 years from date of opening
    if girl_age > 10 or girl_age < 0:
        return {"error": "SSY account can only be opened for girls aged 0-10"}

    r = current_rate / 100
    balance = 0.0

    for year in range(1, maturity_years + 1):
        deposit = annual_deposit if year <= deposit_years else 0
        balance = (balance + deposit) * (1 + r)

    total_deposited = annual_deposit * deposit_years
    total_interest = balance - total_deposited
    wealth_multiplier = round(balance / total_deposited, 2) if total_deposited > 0 else 0

    # Partial withdrawal: 50% of balance at end of previous year allowed after girl turns 18
    partial_withdrawal_age = 18
    partial_withdrawal_year = max(1, partial_withdrawal_age - girl_age)

    return {
        "annual_deposit": annual_deposit,
        "girl_age": girl_age,
        "interest_rate": current_rate,
        "deposit_years": deposit_years,
        "maturity_years": maturity_years,
        "maturity_year_from_now": maturity_years,
        "total_deposited": round(total_deposited, 2),
        "total_interest": round(total_interest, 2),
        "maturity_value": round(balance, 2),
        "wealth_multiplier": wealth_multiplier,
        "tax_benefit_80c": min(round(annual_deposit), 150000),
        "partial_withdrawal_after_year": partial_withdrawal_year,
        "girl_age_at_maturity": girl_age + maturity_years,
        "monthly_deposit_equivalent": round(annual_deposit / 12),
    }


def nps_calculator(monthly_contribution: float, current_age: int,
                   expected_return: float = 10.0, annuity_pct: float = 40.0) -> dict:
    """National Pension System — monthly contribution till 60, with annuity purchase requirement.
    Minimum 40% of corpus must be used to buy annuity; remaining 60% is lump sum (partially taxable)."""
    retirement_age = 60
    years = retirement_age - current_age
    if years <= 0:
        return {"error": "Current age must be less than 60"}

    r_monthly = expected_return / 100 / 12
    months = years * 12

    # Future value of monthly contributions (annuity formula)
    if r_monthly > 0:
        fv = monthly_contribution * (((1 + r_monthly) ** months - 1) / r_monthly) * (1 + r_monthly)
    else:
        fv = monthly_contribution * months

    total_invested = monthly_contribution * months
    total_interest = fv - total_invested
    annuity_investment = fv * (annuity_pct / 100)
    lump_sum = fv - annuity_investment

    # Estimate monthly pension from annuity (assuming 6% annuity rate)
    annuity_rate = 6.0
    est_monthly_pension = annuity_investment * (annuity_rate / 100) / 12

    # Tax benefits: 80CCD(1) up to 1.5L, 80CCD(1B) additional 50K
    annual_contribution = monthly_contribution * 12
    tax_80ccd1 = min(annual_contribution, 150000)
    tax_80ccd1b = min(annual_contribution, 50000)  # additional
    total_annual_tax_saving = (tax_80ccd1 + tax_80ccd1b) * 0.312  # 30% + cess

    # Wealth multiplier
    wealth_multiplier = round(fv / total_invested, 2) if total_invested > 0 else 0

    return {
        "monthly_contribution": monthly_contribution,
        "current_age": current_age,
        "years_to_retire": years,
        "expected_return_pct": expected_return,
        "total_invested": round(total_invested, 2),
        "total_interest": round(total_interest, 2),
        "total_corpus": round(fv, 2),
        "annuity_investment": round(annuity_investment, 2),
        "lump_sum_withdrawal": round(lump_sum, 2),
        "est_monthly_pension": round(est_monthly_pension, 2),
        "annuity_pct": annuity_pct,
        "wealth_multiplier": wealth_multiplier,
        "tax_saving_80ccd1": round(tax_80ccd1),
        "tax_saving_80ccd1b": round(tax_80ccd1b),
        "annual_tax_saved": round(total_annual_tax_saving),
        "total_tax_saved_lifetime": round(total_annual_tax_saving * years),
    }


def swp_calculator(total_investment: float, withdrawal_per_month: float,
                   expected_return: float = 8.0, years: int = 5) -> dict:
    """Systematic Withdrawal Plan — invest lump sum, withdraw monthly while corpus earns returns.
    Uses geometric monthly rate: (1+r)^(1/12)-1 — cross-referenced with Groww."""
    r_monthly = (1 + expected_return / 100) ** (1/12) - 1
    months = years * 12
    balance = total_investment
    total_withdrawn = 0.0

    for m in range(months):
        interest = balance * r_monthly
        balance = balance + interest - withdrawal_per_month
        total_withdrawn += withdrawal_per_month
        if balance <= 0:
            balance = 0
            total_withdrawn -= (withdrawal_per_month + balance)  # adjust last partial
            return {
                "total_investment": total_investment,
                "withdrawal_per_month": withdrawal_per_month,
                "expected_return_pct": expected_return,
                "years": years,
                "total_withdrawn": round(total_withdrawn, 2),
                "final_value": 0,
                "corpus_lasted_months": m + 1,
                "corpus_exhausted": True,
            }

    return {
        "total_investment": total_investment,
        "withdrawal_per_month": withdrawal_per_month,
        "expected_return_pct": expected_return,
        "years": years,
        "total_withdrawn": round(total_withdrawn, 2),
        "final_value": round(balance, 2),
        "corpus_lasted_months": months,
        "corpus_exhausted": False,
        "total_earnings": round(total_withdrawn + balance - total_investment, 2),
        "effective_return": round((total_withdrawn + balance - total_investment) / total_investment * 100, 1),
        "sustainable_withdrawal": round(total_investment * r_monthly, 2),
    }


def nsc_calculator(investment_amount: float, interest_rate: float = 7.7,
                   years: int = 5) -> dict:
    """National Savings Certificate — annual compounding, interest reinvested, paid at maturity.
    Lock-in: 5 years. Tax benefit under 80C up to ₹1.5L."""
    r = interest_rate / 100
    maturity_value = investment_amount * (1 + r) ** years
    total_interest = maturity_value - investment_amount
    tax_benefit_80c = min(investment_amount, 150000)
    return {
        "investment_amount": investment_amount,
        "interest_rate": interest_rate,
        "tenure_years": years,
        "maturity_value": round(maturity_value, 2),
        "total_interest": round(total_interest, 2),
        "effective_yield_pct": round((maturity_value / investment_amount - 1) * 100, 2),
        "tax_benefit_80c": round(tax_benefit_80c, 2),
    }


def gratuity_calculator(basic_salary_monthly: float, years_of_service: float) -> dict:
    """Gratuity as per Payment of Gratuity Act 1972.
    Formula: G = N × B × 15/26
    N = years of service (rounded), B = last drawn basic+DA monthly.
    Maximum exemption: ₹20 lakh."""
    # Round years: >= 6 months rounds up
    import math
    fractional = years_of_service - int(years_of_service)
    if fractional >= 0.5:
        n = int(years_of_service) + 1
    else:
        n = int(years_of_service)

    if n < 5:
        return {"error": "Minimum 5 years of continuous service required for gratuity"}

    gratuity = n * basic_salary_monthly * 15 / 26
    max_exempt = 2000000  # ₹20 lakh
    taxable_gratuity = max(0, gratuity - max_exempt)
    exempt_amount = min(gratuity, max_exempt)

    # Projections at different service years
    projections = {}
    for yr in [5, 10, 15, 20, 25, 30]:
        if yr >= 5:
            proj = yr * basic_salary_monthly * 15 / 26
            projections[f"gratuity_at_{yr}yr"] = round(proj)

    return {
        "basic_salary_monthly": basic_salary_monthly,
        "years_of_service": n,
        "gratuity_amount": round(gratuity, 2),
        "tax_exempt_amount": round(exempt_amount, 2),
        "taxable_amount": round(taxable_gratuity, 2),
        "tax_on_gratuity": round(taxable_gratuity * 0.30) if taxable_gratuity > 0 else 0,
        "net_gratuity": round(gratuity - max(0, taxable_gratuity * 0.30)),
        "max_exemption_limit": max_exempt,
        "monthly_equivalent": round(gratuity / (n * 12)) if n > 0 else 0,
        **projections,
    }


def epf_calculator(basic_salary_monthly: float, current_age: int,
                   employee_contribution_pct: float = 12.0,
                   employer_contribution_pct: float = 12.0,
                   annual_salary_hike_pct: float = 5.0,
                   epf_rate: float = 8.25,
                   existing_balance: float = 0.0) -> dict:
    """Employee Provident Fund calculator.
    Employee contributes 12% of basic+DA. Employer also contributes 12% (EPF+EPS combined).
    Shows total retirement corpus (EPF+EPS) — cross-referenced with Groww.
    Interest compounded monthly at EPF rate."""
    retirement_age = 58
    years = retirement_age - current_age
    if years <= 0:
        return {"error": "Current age must be less than 58 for EPF calculation"}

    r_monthly = epf_rate / 100 / 12
    balance = existing_balance
    total_employee = 0.0
    total_employer = 0.0
    salary = basic_salary_monthly

    for year in range(years):
        for month in range(12):
            emp_contrib = salary * (employee_contribution_pct / 100)
            empr_contrib = salary * (employer_contribution_pct / 100)
            interest = balance * r_monthly
            balance += emp_contrib + empr_contrib + interest
            total_employee += emp_contrib
            total_employer += empr_contrib
        salary *= (1 + annual_salary_hike_pct / 100)

    total_interest = balance - total_employee - total_employer - existing_balance
    total_contributions = total_employee + total_employer
    wealth_multiplier = round(balance / total_contributions, 2) if total_contributions > 0 else 0

    # Estimated monthly pension (using 8% annuity rate on total corpus)
    est_monthly_pension = round(balance * 0.08 / 12)

    # Final salary at retirement
    final_salary = basic_salary_monthly * (1 + annual_salary_hike_pct / 100) ** (years - 1)

    return {
        "current_basic_salary": basic_salary_monthly,
        "current_age": current_age,
        "retirement_age": retirement_age,
        "years_to_retire": years,
        "epf_rate": epf_rate,
        "total_employee_contribution": round(total_employee, 2),
        "total_employer_contribution": round(total_employer, 2),
        "total_contributions": round(total_contributions, 2),
        "total_interest_earned": round(total_interest, 2),
        "maturity_value": round(balance, 2),
        "wealth_multiplier": wealth_multiplier,
        "est_monthly_pension": est_monthly_pension,
        "final_basic_salary": round(final_salary),
        "existing_balance": existing_balance,
    }


def scss_calculator(investment_amount: float, interest_rate: float = 8.2,
                    tenure_years: int = 5) -> dict:
    """Senior Citizens Savings Scheme — simple interest paid quarterly.
    Max investment: ₹30 lakh. Tenure: 5 years (extendable by 3).
    Tax benefit under 80C."""
    if investment_amount > 3000000:
        return {"error": "Maximum SCSS investment is ₹30 lakh"}

    quarterly_interest = investment_amount * (interest_rate / 100) / 4
    total_quarters = tenure_years * 4
    total_interest = quarterly_interest * total_quarters
    maturity_value = investment_amount + total_interest
    annual_income = quarterly_interest * 4
    return {
        "investment_amount": investment_amount,
        "interest_rate": interest_rate,
        "tenure_years": tenure_years,
        "quarterly_interest": round(quarterly_interest, 2),
        "annual_income": round(annual_income, 2),
        "total_interest": round(total_interest, 2),
        "maturity_value": round(maturity_value, 2),
        "tax_benefit_80c": round(min(investment_amount, 150000), 2),
    }


def post_office_mis_calculator(investment_amount: float,
                                interest_rate: float = 7.4) -> dict:
    """Post Office Monthly Income Scheme — fixed monthly income for 5 years.
    Max: ₹9 lakh (single), ₹15 lakh (joint). Simple interest paid monthly."""
    tenure_years = 5
    monthly_interest = investment_amount * (interest_rate / 100) / 12
    total_interest = monthly_interest * tenure_years * 12
    maturity_value = investment_amount  # principal returned at maturity
    return {
        "investment_amount": investment_amount,
        "interest_rate": interest_rate,
        "tenure_years": tenure_years,
        "monthly_income": round(monthly_interest, 2),
        "annual_income": round(monthly_interest * 12, 2),
        "total_interest": round(total_interest, 2),
        "maturity_value": round(maturity_value, 2),
    }


def apy_calculator(monthly_contribution: float, current_age: int,
                   desired_pension: float = 5000) -> dict:
    """Atal Pension Yojana — government pension scheme for unorganised sector.
    Age 18-40 eligible. Pension starts at 60. Fixed pension: ₹1000-5000/month."""
    if current_age < 18 or current_age > 40:
        return {"error": "APY is available for ages 18-40 only"}

    years_to_contribute = 60 - current_age
    months = years_to_contribute * 12
    total_invested = monthly_contribution * months

    # APY pension amounts are fixed by govt. We estimate corpus needed.
    # For ₹5000/month pension, approx corpus needed is ~₹8.5L
    pension_corpus_map = {1000: 170000, 2000: 340000, 3000: 510000, 4000: 680000, 5000: 850000}

    # Find closest pension slab
    pension_slabs = [1000, 2000, 3000, 4000, 5000]
    closest_pension = min(pension_slabs, key=lambda x: abs(x - desired_pension))
    estimated_corpus = pension_corpus_map.get(closest_pension, 850000)

    return {
        "monthly_contribution": monthly_contribution,
        "current_age": current_age,
        "years_to_contribute": years_to_contribute,
        "total_invested": round(total_invested, 2),
        "monthly_pension_at_60": closest_pension,
        "estimated_corpus": estimated_corpus,
        "spouse_pension": closest_pension,  # same pension to spouse after death
        "nominee_receives": estimated_corpus,  # corpus to nominee after both deaths
    }


def gst_calculator(amount: float, gst_rate: float = 18.0,
                   is_inclusive: bool = False) -> dict:
    """GST Calculator — compute GST amount, CGST, SGST from pre/post-tax amount."""
    if is_inclusive:
        # Amount includes GST, find base
        base_amount = amount / (1 + gst_rate / 100)
        gst_amount = amount - base_amount
    else:
        base_amount = amount
        gst_amount = amount * (gst_rate / 100)

    total = base_amount + gst_amount
    cgst = gst_amount / 2  # Central GST
    sgst = gst_amount / 2  # State GST (or IGST for interstate)
    return {
        "base_amount": round(base_amount, 2),
        "gst_rate": gst_rate,
        "gst_amount": round(gst_amount, 2),
        "cgst": round(cgst, 2),
        "sgst": round(sgst, 2),
        "total_amount": round(total, 2),
        "is_inclusive": is_inclusive,
    }


def tds_calculator(income: float, income_type: str = "salary",
                   pan_available: bool = True) -> dict:
    """TDS (Tax Deducted at Source) calculator for common income types."""
    tds_rates = {
        "salary": {"with_pan": 10.0, "without_pan": 20.0, "threshold": 250000},
        "interest": {"with_pan": 10.0, "without_pan": 20.0, "threshold": 40000},
        "rent": {"with_pan": 10.0, "without_pan": 20.0, "threshold": 240000},
        "professional_fees": {"with_pan": 10.0, "without_pan": 20.0, "threshold": 30000},
        "commission": {"with_pan": 5.0, "without_pan": 20.0, "threshold": 15000},
        "dividend": {"with_pan": 10.0, "without_pan": 20.0, "threshold": 5000},
        "lottery": {"with_pan": 30.0, "without_pan": 30.0, "threshold": 10000},
        "property_sale": {"with_pan": 1.0, "without_pan": 20.0, "threshold": 5000000},
    }

    if income_type not in tds_rates:
        return {"error": f"Unknown income type. Use: {', '.join(tds_rates.keys())}"}

    rates = tds_rates[income_type]
    threshold = rates["threshold"]
    rate = rates["with_pan"] if pan_available else rates["without_pan"]

    if income <= threshold:
        tds = 0
    else:
        tds = income * (rate / 100)

    return {
        "income": income,
        "income_type": income_type,
        "pan_available": pan_available,
        "threshold": threshold,
        "tds_rate_pct": rate,
        "tds_amount": round(tds, 2),
        "net_amount": round(income - tds, 2),
    }


def simple_interest(principal: float, rate: float, years: float) -> dict:
    """Simple interest calculator."""
    interest = principal * (rate / 100) * years
    total = principal + interest
    return {
        "principal": principal,
        "rate": rate,
        "years": years,
        "interest": round(interest, 2),
        "total_amount": round(total, 2),
    }


def flat_vs_reducing_rate(principal: float, flat_rate: float,
                          reducing_rate: float, tenure_months: int) -> dict:
    """Compare flat rate vs reducing balance rate for loans."""
    # Flat rate EMI
    flat_interest = principal * (flat_rate / 100) * (tenure_months / 12)
    flat_total = principal + flat_interest
    flat_emi = flat_total / tenure_months

    # Reducing rate EMI (standard amortization)
    r = reducing_rate / 100 / 12
    if r > 0:
        reducing_emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    else:
        reducing_emi = principal / tenure_months
    reducing_total = reducing_emi * tenure_months
    reducing_interest = reducing_total - principal

    savings = flat_total - reducing_total
    return {
        "principal": principal,
        "tenure_months": tenure_months,
        "flat_rate": flat_rate,
        "flat_emi": round(flat_emi, 2),
        "flat_total_interest": round(flat_interest, 2),
        "flat_total_payment": round(flat_total, 2),
        "reducing_rate": reducing_rate,
        "reducing_emi": round(reducing_emi, 2),
        "reducing_total_interest": round(reducing_interest, 2),
        "reducing_total_payment": round(reducing_total, 2),
        "savings_with_reducing": round(savings, 2),
        "better_option": "Reducing Balance" if savings > 0 else "Flat Rate",
    }


def stock_average_calculator(purchases: list) -> dict:
    """Calculate average price of stock purchases.
    purchases: list of {"qty": int, "price": float}"""
    if not purchases or len(purchases) == 0:
        return {"error": "Provide at least one purchase with qty and price"}

    total_qty = 0
    total_cost = 0.0
    for p in purchases:
        qty = float(p.get("qty", 0))
        price = float(p.get("price", 0))
        total_qty += qty
        total_cost += qty * price

    if total_qty == 0:
        return {"error": "Total quantity cannot be zero"}

    avg_price = total_cost / total_qty
    return {
        "total_quantity": int(total_qty),
        "total_investment": round(total_cost, 2),
        "average_price": round(avg_price, 2),
        "num_purchases": len(purchases),
    }


def kvp_calculator(investment_amount: float, interest_rate: float = 7.5) -> dict:
    """Kisan Vikas Patra — doubles your investment. Compounded annually.
    Current rate ~7.5%, doubles in ~115 months."""
    r = interest_rate / 100
    # Time to double: 72/rate (approx) or exact: log(2)/log(1+r)
    import math
    years_to_double = math.log(2) / math.log(1 + r)
    months_to_double = int(years_to_double * 12)
    maturity_value = investment_amount * 2
    total_interest = investment_amount
    return {
        "investment_amount": investment_amount,
        "interest_rate": interest_rate,
        "maturity_value": round(maturity_value, 2),
        "total_interest": round(total_interest, 2),
        "years_to_double": round(years_to_double, 1),
        "months_to_double": months_to_double,
    }


def mutual_fund_returns(investment_amount: float, annual_return: float,
                        years: int, expense_ratio: float = 1.5,
                        is_sip: bool = False) -> dict:
    """Mutual Fund returns calculator — accounts for expense ratio.
    Works for both lumpsum and SIP modes."""
    net_return = annual_return - expense_ratio
    if net_return < 0:
        net_return = 0

    if is_sip:
        # SIP mode — monthly compounding
        r = net_return / 100 / 12
        months = years * 12
        if r > 0:
            fv = investment_amount * (((1 + r) ** months - 1) / r) * (1 + r)
        else:
            fv = investment_amount * months
        total_invested = investment_amount * months
    else:
        # Lumpsum mode
        fv = investment_amount * (1 + net_return / 100) ** years
        total_invested = investment_amount

    wealth_gained = fv - total_invested
    # Compare with gross (no expense ratio)
    if is_sip:
        r_gross = annual_return / 100 / 12
        months = years * 12
        fv_gross = investment_amount * (((1 + r_gross) ** months - 1) / r_gross) * (1 + r_gross) if r_gross > 0 else investment_amount * months
    else:
        fv_gross = investment_amount * (1 + annual_return / 100) ** years
    expense_ratio_impact = fv_gross - fv

    return {
        "investment_amount": investment_amount,
        "annual_return_pct": annual_return,
        "expense_ratio_pct": expense_ratio,
        "net_return_pct": round(net_return, 2),
        "years": years,
        "mode": "SIP" if is_sip else "Lumpsum",
        "total_invested": round(total_invested, 2),
        "future_value": round(fv, 2),
        "wealth_gained": round(wealth_gained, 2),
        "expense_ratio_impact": round(expense_ratio_impact, 2),
    }


# ──────────────────────── Lumpsum Calculator ────────────────────────

def lumpsum_calculator(principal: float, annual_rate: float, years: int) -> dict:
    """Calculate lumpsum mutual fund / investment returns.

    Formula: A = P × (1 + r)^t  (annual compounding, standard for MF NAV growth).
    Cross-referenced with Groww, ET Money, ClearTax lumpsum calculators.
    """
    future_value = principal * (1 + annual_rate / 100) ** years
    wealth_gained = future_value - principal
    absolute_return_pct = (wealth_gained / principal) * 100 if principal > 0 else 0
    # CAGR is simply the input rate for lumpsum, but we verify:
    cagr = ((future_value / principal) ** (1 / years) - 1) * 100 if (principal > 0 and years > 0) else 0

    # Delay cost
    delay_costs = {}
    for delay in [1, 3, 5]:
        if years - delay > 0:
            fv_d = principal * (1 + annual_rate / 100) ** (years - delay)
            delay_costs[f"delay_{delay}yr_loss"] = round(future_value - fv_d)

    # Doubling time (Rule of 72)
    doubling_years = round(72 / annual_rate, 1) if annual_rate > 0 else 0

    # Inflation-adjusted (real) return
    inflation = 6.0
    real_return = ((1 + annual_rate / 100) / (1 + inflation / 100) - 1) * 100
    real_future_value = principal * (1 + real_return / 100) ** years

    return {
        "invested_amount": round(principal),
        "annual_rate": annual_rate,
        "years": years,
        "future_value": round(future_value),
        "wealth_gained": round(wealth_gained),
        "absolute_return_pct": round(absolute_return_pct, 1),
        "cagr_pct": round(cagr, 2),
        "wealth_multiplier": round(future_value / principal, 2) if principal > 0 else 0,
        "doubling_time_years": doubling_years,
        "real_return_pct": round(real_return, 2),
        "inflation_adjusted_value": round(real_future_value),
        **delay_costs,
    }


# ──────────────────────── XIRR Calculator ────────────────────────

def xirr_calculator(cashflows: list[dict]) -> dict:
    """Calculate XIRR (Extended Internal Rate of Return) using Newton-Raphson.

    XIRR solves: Σ C_i / (1 + rate)^((d_i - d_0) / 365) = 0

    Args:
        cashflows: list of {"date": "YYYY-MM-DD", "amount": float}
                   Negative = investment/outflow, Positive = redemption/inflow.
                   Must have at least one negative and one positive.

    Cross-referenced with Excel XIRR, Groww, Zerodha Coin methodologies.
    Uses Newton-Raphson iteration (same as Excel).
    """
    from datetime import datetime

    if len(cashflows) < 2:
        return {"error": "Need at least 2 cashflows (investment + redemption)"}

    # Parse and sort by date
    parsed = []
    for cf in cashflows:
        try:
            d = datetime.strptime(cf["date"], "%Y-%m-%d")
        except (ValueError, KeyError):
            return {"error": f"Invalid date format: {cf.get('date', '?')}. Use YYYY-MM-DD"}
        try:
            amt = float(cf["amount"])
        except (ValueError, KeyError):
            return {"error": f"Invalid amount: {cf.get('amount', '?')}"}
        parsed.append((d, amt))

    parsed.sort(key=lambda x: x[0])
    dates = [p[0] for p in parsed]
    amounts = [p[1] for p in parsed]

    has_neg = any(a < 0 for a in amounts)
    has_pos = any(a > 0 for a in amounts)
    if not (has_neg and has_pos):
        return {"error": "Need at least one investment (negative) and one redemption (positive)"}

    d0 = dates[0]
    # Year fractions from first date
    years_frac = [(d - d0).days / 365.0 for d in dates]

    # Newton-Raphson to solve Σ amounts[i] / (1+rate)^years_frac[i] = 0
    def npv(rate):
        return sum(a / (1 + rate) ** y for a, y in zip(amounts, years_frac))

    def npv_deriv(rate):
        return sum(-y * a / (1 + rate) ** (y + 1) for a, y in zip(amounts, years_frac))

    rate = 0.1  # initial guess 10%
    for _ in range(200):
        nv = npv(rate)
        nd = npv_deriv(rate)
        if abs(nd) < 1e-14:
            break
        new_rate = rate - nv / nd
        # Clamp to avoid divergence
        if new_rate <= -1:
            new_rate = (rate - 1) / 2
        if abs(new_rate - rate) < 1e-9:
            rate = new_rate
            break
        rate = new_rate

    # Verify convergence
    if abs(npv(rate)) > 0.01:
        return {"error": "XIRR did not converge — check your cashflows"}

    total_invested = sum(abs(a) for a in amounts if a < 0)
    total_received = sum(a for a in amounts if a > 0)
    net_gain = total_received - total_invested
    holding_days = (dates[-1] - dates[0]).days

    return {
        "xirr_pct": round(rate * 100, 2),
        "total_invested": round(total_invested),
        "total_received": round(total_received),
        "net_gain": round(net_gain),
        "absolute_return_pct": round(net_gain / total_invested * 100, 2) if total_invested > 0 else 0,
        "holding_period_days": holding_days,
        "num_transactions": len(cashflows),
    }


def xirr_sip_calculator(sip_amount: float, num_months: int,
                        maturity_value: float, start_date: str = "2024-01-01") -> dict:
    """Simplified XIRR for SIP — calculates XIRR given monthly SIP and final value.

    This is the Groww-style XIRR calculator: provide SIP amount, duration,
    and maturity amount to get the XIRR.
    """
    from datetime import datetime, timedelta

    if num_months < 1:
        return {"error": "Number of months must be at least 1"}
    if maturity_value <= 0:
        return {"error": "Maturity value must be positive"}

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        return {"error": f"Invalid start date: {start_date}. Use YYYY-MM-DD"}

    # Build cashflows: monthly SIP (negative) + final redemption (positive)
    cashflows = []
    for i in range(num_months):
        d = start + timedelta(days=i * 30)  # approximate monthly
        cashflows.append({"date": d.strftime("%Y-%m-%d"), "amount": -sip_amount})

    # Maturity date
    maturity_date = start + timedelta(days=num_months * 30)
    cashflows.append({"date": maturity_date.strftime("%Y-%m-%d"), "amount": maturity_value})

    result = xirr_calculator(cashflows)
    if "error" in result:
        return result

    result["sip_amount"] = sip_amount
    result["num_months"] = num_months
    result["maturity_value"] = round(maturity_value)
    return result
