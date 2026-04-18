"""
Calculator Registry — defines standalone financial calculators with
field definitions, validation, and result formatting.
Each calculator maps directly to a function in financial_calc.py.
"""

from tools.financial_calc import (
    sip_calculator, emi_calculator, compound_interest, retirement_corpus,
    tax_bracket_india, ctc_to_take_home, ppf_calculator, fd_calculator,
    goal_sip, loan_prepayment, hra_exemption, fire_calculator,
    lumpsum_vs_sip, stepup_sip, capital_gains_tax, education_loan_calc,
    inflation_goal_planner, salary_hike_impact,
    # Groww-style additions
    rd_calculator, ssy_calculator, nps_calculator, swp_calculator,
    nsc_calculator, gratuity_calculator, epf_calculator, scss_calculator,
    post_office_mis_calculator, apy_calculator, gst_calculator,
    tds_calculator, simple_interest, flat_vs_reducing_rate,
    kvp_calculator, mutual_fund_returns,
    lumpsum_calculator, xirr_sip_calculator,
)

# ──────────────────────── Field Types ────────────────────────
# Each field: { id, label, type, placeholder, [min], [max], [default], [suffix], [options], [required] }

CALCULATORS = {
    "sip": {
        "name": "SIP Calculator",
        "icon": "📈",
        "description": "Calculate returns on Systematic Investment Plan",
        "fields": [
            {"id": "monthly_investment", "label": "Monthly Investment", "type": "number", "placeholder": "10000", "min": 100, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Expected Annual Return", "type": "number", "placeholder": "12", "min": 0, "max": 50, "suffix": "%", "required": True},
            {"id": "years", "label": "Investment Period", "type": "number", "placeholder": "10", "min": 1, "max": 50, "suffix": "years", "required": True},
        ],
        "fn": lambda d: sip_calculator(d["monthly_investment"], d["annual_rate"], d["years"]),
        "result_format": [
            {"key": "total_invested", "label": "Total Invested", "fmt": "currency"},
            {"key": "future_value", "label": "Future Value", "fmt": "currency"},
            {"key": "wealth_gained", "label": "Wealth Gained", "fmt": "currency"},
            {"key": "absolute_return_pct", "label": "Absolute Return", "fmt": "pct"},
            {"key": "wealth_multiplier", "label": "Wealth Multiplier", "fmt": "number"},
            {"key": "delay_1yr_loss", "label": "\u23f3 Cost of 1-Year Delay", "fmt": "currency"},
            {"key": "delay_3yr_loss", "label": "\u23f3 Cost of 3-Year Delay", "fmt": "currency"},
            {"key": "delay_5yr_loss", "label": "\u23f3 Cost of 5-Year Delay", "fmt": "currency"},
        ],
    },

    "lumpsum": {
        "name": "Lumpsum Calculator",
        "icon": "💰",
        "description": "Calculate returns on one-time mutual fund / investment",
        "fields": [
            {"id": "principal", "label": "Investment Amount", "type": "number", "placeholder": "500000", "min": 100, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Expected Annual Return", "type": "number", "placeholder": "12", "min": 0, "max": 50, "suffix": "%", "required": True},
            {"id": "years", "label": "Investment Period", "type": "number", "placeholder": "10", "min": 1, "max": 50, "suffix": "years", "required": True},
        ],
        "fn": lambda d: lumpsum_calculator(d["principal"], d["annual_rate"], int(d["years"])),
        "result_format": [
            {"key": "invested_amount", "label": "Invested Amount", "fmt": "currency"},
            {"key": "future_value", "label": "Future Value", "fmt": "currency"},
            {"key": "wealth_gained", "label": "Wealth Gained", "fmt": "currency"},
            {"key": "absolute_return_pct", "label": "Absolute Return", "fmt": "pct"},
            {"key": "cagr_pct", "label": "CAGR", "fmt": "pct"},
            {"key": "wealth_multiplier", "label": "Wealth Multiplier", "fmt": "number"},
            {"key": "doubling_time_years", "label": "Doubling Time (Rule of 72)", "fmt": "number"},
            {"key": "real_return_pct", "label": "Real Return (after 6% inflation)", "fmt": "pct"},
            {"key": "inflation_adjusted_value", "label": "Inflation-Adjusted Value", "fmt": "currency"},
            {"key": "delay_1yr_loss", "label": "\u23f3 Cost of 1-Year Delay", "fmt": "currency"},
            {"key": "delay_3yr_loss", "label": "\u23f3 Cost of 3-Year Delay", "fmt": "currency"},
            {"key": "delay_5yr_loss", "label": "\u23f3 Cost of 5-Year Delay", "fmt": "currency"},
        ],
    },

    "emi": {
        "name": "EMI Calculator",
        "icon": "🏠",
        "description": "Calculate monthly EMI for home, car, or personal loans",
        "fields": [
            {"id": "principal", "label": "Loan Amount", "type": "number", "placeholder": "5000000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Interest Rate", "type": "number", "placeholder": "8.5", "min": 0, "max": 50, "suffix": "%", "required": True},
            {"id": "tenure_months", "label": "Loan Tenure", "type": "number", "placeholder": "240", "min": 1, "max": 480, "suffix": "months", "required": True},
        ],
        "fn": lambda d: emi_calculator(d["principal"], d["annual_rate"], d["tenure_months"]),
        "result_format": [
            {"key": "emi", "label": "Monthly EMI", "fmt": "currency"},
            {"key": "total_payment", "label": "Total Payment", "fmt": "currency"},
            {"key": "total_interest", "label": "Total Interest", "fmt": "currency"},
            {"key": "interest_to_principal_ratio", "label": "Interest / Principal", "fmt": "pct"},
            {"key": "tenure_years", "label": "Tenure (Years)", "fmt": "number"},
            {"key": "first_month_interest", "label": "1st Month Interest Portion", "fmt": "currency"},
            {"key": "first_month_principal", "label": "1st Month Principal Portion", "fmt": "currency"},
            {"key": "processing_fee_est", "label": "Est. Processing Fee (1%)", "fmt": "currency"},
            {"key": "min_monthly_income_needed", "label": "Min Income Needed (40% rule)", "fmt": "currency"},
        ],
    },

    "compound_interest": {
        "name": "Compound Interest",
        "icon": "💰",
        "description": "Calculate compound interest on lump sum investment",
        "fields": [
            {"id": "principal", "label": "Principal Amount", "type": "number", "placeholder": "100000", "min": 1, "suffix": "₹", "required": True},
            {"id": "rate", "label": "Annual Interest Rate", "type": "number", "placeholder": "8", "min": 0, "max": 50, "suffix": "%", "required": True},
            {"id": "years", "label": "Time Period", "type": "number", "placeholder": "5", "min": 1, "max": 50, "suffix": "years", "required": True},
            {"id": "compounding", "label": "Compounding", "type": "select", "options": [
                {"value": "12", "label": "Monthly"},
                {"value": "4", "label": "Quarterly"},
                {"value": "2", "label": "Half-Yearly"},
                {"value": "1", "label": "Annually"},
            ], "default": "12"},
        ],
        "fn": lambda d: compound_interest(d["principal"], d["rate"], d["years"], int(d.get("compounding", 12))),
        "result_format": [
            {"key": "principal", "label": "Principal", "fmt": "currency"},
            {"key": "final_amount", "label": "Maturity Amount", "fmt": "currency"},
            {"key": "total_interest", "label": "Interest Earned", "fmt": "currency"},
            {"key": "effective_rate", "label": "Effective Rate", "fmt": "pct"},
        ],
    },

    "retirement": {
        "name": "Retirement Planner",
        "icon": "🏖️",
        "description": "Calculate corpus needed and monthly SIP for retirement",
        "fields": [
            {"id": "monthly_expense", "label": "Current Monthly Expenses", "type": "number", "placeholder": "50000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "years_to_retire", "label": "Years to Retirement", "type": "number", "placeholder": "25", "min": 1, "max": 50, "suffix": "years", "required": True},
            {"id": "years_in_retirement", "label": "Years in Retirement", "type": "number", "placeholder": "25", "min": 1, "max": 50, "suffix": "years", "required": True},
            {"id": "inflation_rate", "label": "Expected Inflation", "type": "number", "placeholder": "6", "min": 0, "max": 20, "suffix": "%", "default": "6"},
            {"id": "expected_return", "label": "Expected Return", "type": "number", "placeholder": "12", "min": 0, "max": 30, "suffix": "%", "default": "12"},
        ],
        "fn": lambda d: retirement_corpus(d["monthly_expense"], d.get("inflation_rate", 6), d["years_to_retire"], d["years_in_retirement"], d.get("expected_return", 12)),
        "result_format": [
            {"key": "current_monthly_expense", "label": "Current Monthly Expense", "fmt": "currency"},
            {"key": "future_monthly_expense", "label": "Monthly Expense at Retirement", "fmt": "currency"},
            {"key": "expense_inflation_multiplier", "label": "Expense Multiplier", "fmt": "number"},
            {"key": "corpus_needed", "label": "Retirement Corpus Needed", "fmt": "currency"},
            {"key": "monthly_sip_needed", "label": "Monthly SIP Required", "fmt": "currency"},
            {"key": "stepup_sip_start_10pct", "label": "Step-Up SIP (10%/yr) Start", "fmt": "currency"},
            {"key": "stepup_sip_saving", "label": "Monthly Saving vs Flat SIP", "fmt": "currency"},
            {"key": "lumpsum_needed_today", "label": "Lumpsum Needed Today", "fmt": "currency"},
            {"key": "total_sip_invested", "label": "Total SIP Investment", "fmt": "currency"},
            {"key": "wealth_from_compounding", "label": "Wealth from Compounding", "fmt": "currency"},
            {"key": "wealth_multiplier", "label": "Wealth Multiplier", "fmt": "number"},
            {"key": "emergency_fund_6mo", "label": "Emergency Fund (6 months)", "fmt": "currency"},
            {"key": "total_corpus_with_emergency", "label": "Total with Emergency Buffer", "fmt": "currency"},
        ],
    },

    "tax_india": {
        "name": "Income Tax Calculator",
        "icon": "🏛️",
        "description": "Calculate Indian income tax — New vs Old regime (FY 2025-26)",
        "fields": [
            {"id": "taxable_income", "label": "Annual Gross Income", "type": "number", "placeholder": "1200000", "min": 0, "suffix": "₹", "required": True},
            {"id": "regime", "label": "Tax Regime", "type": "select", "options": [
                {"value": "new", "label": "New Regime (2025-26)"},
                {"value": "old", "label": "Old Regime"},
                {"value": "both", "label": "Compare Both"},
            ], "default": "both"},
        ],
        "fn": "_tax_compare",  # Special handler
        "result_format": [],  # Dynamic
    },

    "ctc": {
        "name": "CTC to Take-Home",
        "icon": "💼",
        "description": "Ultimate CTC breakdown — salary structure, deductions, HRA exemption, New vs Old regime comparison",
        "fields": [
            {"id": "ctc_annual", "label": "Annual CTC", "type": "number", "placeholder": "1200000", "min": 100000, "suffix": "₹", "required": True},
            {"id": "basic_pct", "label": "Basic % of CTC", "type": "number", "placeholder": "50", "min": 20, "max": 80, "suffix": "%", "default": "50"},
            {"id": "bonus_in_ctc", "label": "Bonus / Variable Pay in CTC", "type": "number", "placeholder": "0", "min": 0, "suffix": "₹", "default": "0"},
            {"id": "is_metro", "label": "City Type", "type": "select", "options": [
                {"value": "true", "label": "Metro (Mumbai/Delhi/Bangalore/Chennai/Kolkata/Hyderabad)"},
                {"value": "false", "label": "Non-Metro / Tier-2 City"},
            ], "default": "true"},
            {"id": "monthly_rent", "label": "Monthly Rent Paid", "type": "number", "placeholder": "0", "min": 0, "suffix": "₹", "default": "0"},
            {"id": "deductions_80c", "label": "Additional 80C (ELSS/PPF/LIC)", "type": "number", "placeholder": "0", "min": 0, "max": 150000, "suffix": "₹", "default": "0"},
            {"id": "section_80d_self", "label": "Health Insurance 80D (Self)", "type": "number", "placeholder": "0", "min": 0, "max": 25000, "suffix": "₹", "default": "0"},
            {"id": "lta_annual", "label": "LTA (Annual)", "type": "number", "placeholder": "0", "min": 0, "suffix": "₹", "default": "0"},
            {"id": "food_coupons_monthly", "label": "Food Coupons / Meal Vouchers (Monthly)", "type": "number", "placeholder": "0", "min": 0, "suffix": "₹", "default": "0"},
            {"id": "nps_employer_pct", "label": "Employer NPS (% of Basic)", "type": "number", "placeholder": "0", "min": 0, "max": 14, "suffix": "%", "default": "0"},
            {"id": "monthly_additional_deduction", "label": "Other Monthly Deductions", "type": "number", "placeholder": "0", "min": 0, "suffix": "₹", "default": "0"},
        ],
        "fn": lambda d: ctc_to_take_home(
            d["ctc_annual"],
            d.get("basic_pct", 50) / 100,
            additional_80c=d.get("deductions_80c", 0),
            bonus_in_ctc=d.get("bonus_in_ctc", 0),
            is_metro=str(d.get("is_metro", "true")).lower() == "true",
            monthly_rent=d.get("monthly_rent", 0),
            lta_annual=d.get("lta_annual", 0),
            food_coupons_monthly=d.get("food_coupons_monthly", 0),
            nps_employer_pct=d.get("nps_employer_pct", 0),
            monthly_additional_deduction=d.get("monthly_additional_deduction", 0),
            section_80d_self=d.get("section_80d_self", 0),
        ),
        "result_format": [
            # ── CTC Salary Structure ──
            {"label": "📋 CTC Salary Structure", "fmt": "section"},
            {"key": "ctc_annual", "label": "Annual CTC", "fmt": "currency"},
            {"key": "basic", "label": "Basic (Annual)", "fmt": "currency"},
            {"key": "basic_monthly", "label": "Basic (Monthly)", "fmt": "currency"},
            {"key": "hra", "label": "HRA (Annual)", "fmt": "currency"},
            {"key": "hra_monthly", "label": "HRA (Monthly)", "fmt": "currency"},
            {"key": "city_type", "label": "City Type", "fmt": "text"},
            {"key": "special_allowance", "label": "Special Allowance (Annual)", "fmt": "currency"},
            {"key": "special_allowance_monthly", "label": "Special Allowance (Monthly)", "fmt": "currency"},
            {"key": "bonus_annual", "label": "Bonus / Variable Pay", "fmt": "currency"},
            {"key": "lta_annual", "label": "LTA (Annual)", "fmt": "currency"},
            {"key": "food_coupons_annual", "label": "Food Coupons (Annual)", "fmt": "currency"},
            # ── Employer Deductions from CTC ──
            {"label": "🏢 Employer Deductions (from CTC)", "fmt": "section"},
            {"key": "epf_employer_total", "label": "Employer EPF (12% of Basic)", "fmt": "currency"},
            {"key": "eps_contribution", "label": "↳ EPS Pension (8.33%, capped)", "fmt": "currency"},
            {"key": "epf_employer_epf", "label": "↳ EPF Account (3.67%+)", "fmt": "currency"},
            {"key": "edli", "label": "EDLI Insurance (0.5%)", "fmt": "currency"},
            {"key": "gratuity_annual_provision", "label": "Gratuity Provision (4.81%)", "fmt": "currency"},
            {"key": "nps_employer", "label": "Employer NPS", "fmt": "currency"},
            {"key": "medical_insurance_employer", "label": "Medical Insurance (Employer)", "fmt": "currency"},
            {"key": "gross_salary", "label": "Gross Salary (CTC − Employer costs)", "fmt": "currency"},
            {"key": "gross_monthly", "label": "Gross Salary (Monthly)", "fmt": "currency"},
            # ── Employee Deductions ──
            {"label": "📤 Employee Deductions (from Salary)", "fmt": "section"},
            {"key": "epf_employee", "label": "Employee EPF (12% of Basic)", "fmt": "currency"},
            {"key": "epf_employee_monthly", "label": "Employee EPF (Monthly)", "fmt": "currency"},
            {"key": "professional_tax", "label": "Professional Tax (Annual)", "fmt": "currency"},
            {"key": "additional_deduction_annual", "label": "Other Deductions (Annual)", "fmt": "currency"},
            # ── Tax Exemptions (Old Regime) ──
            {"label": "🛡️ Tax Exemptions & Deductions (Old Regime)", "fmt": "section"},
            {"key": "hra_exempt", "label": "HRA Exemption (Old Regime)", "fmt": "currency"},
            {"key": "rent_monthly", "label": "Monthly Rent Paid", "fmt": "currency"},
            {"key": "food_coupons_exempt", "label": "Food Coupons Exempt (max ₹26,400)", "fmt": "currency"},
            {"key": "section_80c_total", "label": "80C Used (EPF + Additional)", "fmt": "currency"},
            {"key": "section_80c_remaining", "label": "80C Limit Remaining", "fmt": "currency"},
            {"key": "section_80d_self", "label": "80D Health Insurance (Self)", "fmt": "currency"},
            {"key": "old_regime_total_deductions", "label": "Total Old Regime Deductions", "fmt": "currency"},
            # ── New vs Old Regime Comparison (table) ──
            {"label": "⚖️ New Regime vs Old Regime", "fmt": "compare_start", "col_new": "New Regime", "col_old": "Old Regime"},
            {"key_new": "tax_new_regime", "key_old": "tax_old_regime", "label": "Income Tax (Annual)", "fmt": "compare", "val_fmt": "currency"},
            {"key_new": "tax_new_monthly", "key_old": "tax_old_monthly", "label": "Income Tax (Monthly)", "fmt": "compare", "val_fmt": "currency"},
            {"key_new": "effective_tax_rate_new", "key_old": "effective_tax_rate_old", "label": "Effective Tax Rate", "fmt": "compare", "val_fmt": "pct"},
            {"key_new": "total_deductions_monthly_new", "key_old": "total_deductions_monthly_old", "label": "Total Deductions/Month", "fmt": "compare", "val_fmt": "currency"},
            {"key_new": "take_home_monthly_new", "key_old": "take_home_monthly_old", "label": "Monthly In-Hand", "fmt": "compare", "val_fmt": "currency"},
            {"key_new": "take_home_annual_new", "key_old": "take_home_annual_old", "label": "Annual Take-Home", "fmt": "compare", "val_fmt": "currency"},
            {"fmt": "compare_end"},
            # ── Verdict ──
            {"key": "better_regime", "label": "✅ Better Regime", "fmt": "text"},
            {"key": "regime_savings", "label": "You Save (per year)", "fmt": "currency"},
            # ── Retirement ──
            {"label": "🏦 Retirement Accrual", "fmt": "section"},
            {"key": "total_retirement_annual", "label": "Total Retirement/Year (EPF+Gratuity)", "fmt": "currency"},
            {"key": "total_retirement_monthly", "label": "Total Retirement/Month", "fmt": "currency"},
            {"key": "gratuity_5yr", "label": "Gratuity at 5 Years", "fmt": "currency"},
            {"key": "gratuity_10yr", "label": "Gratuity at 10 Years", "fmt": "currency"},
        ],
    },

    "ppf": {
        "name": "PPF Calculator",
        "icon": "🏦",
        "description": "Calculate Public Provident Fund maturity with yearly deposits",
        "fields": [
            {"id": "annual_deposit", "label": "Annual Deposit", "type": "number", "placeholder": "150000", "min": 500, "max": 150000, "suffix": "₹", "required": True},
            {"id": "years", "label": "Duration", "type": "number", "placeholder": "15", "min": 15, "max": 50, "suffix": "years", "default": "15"},
            {"id": "current_rate", "label": "PPF Interest Rate", "type": "number", "placeholder": "7.1", "min": 1, "max": 15, "suffix": "%", "default": "7.1"},
        ],
        "fn": lambda d: ppf_calculator(d["annual_deposit"], int(d.get("years", 15)), d.get("current_rate", 7.1)),
        "result_format": [
            {"key": "total_invested", "label": "Total Deposited", "fmt": "currency"},
            {"key": "maturity_value", "label": "Maturity Value", "fmt": "currency"},
            {"key": "total_interest", "label": "Interest Earned", "fmt": "currency"},
            {"key": "wealth_multiplier", "label": "Wealth Multiplier", "fmt": "number"},
            {"key": "tax_benefit_80c", "label": "Section 80C Benefit", "fmt": "currency"},
            {"key": "monthly_deposit_equivalent", "label": "Monthly Equivalent", "fmt": "currency"},
            {"key": "ppf_advantage_over_fd", "label": "PPF Advantage over Taxable FD", "fmt": "currency"},
            {"key": "partial_withdrawal_from_year", "label": "Partial Withdrawal From Year", "fmt": "number"},
            {"key": "loan_available_year", "label": "Loan Facility From Year", "fmt": "number"},
        ],
    },

    "fd": {
        "name": "FD Calculator",
        "icon": "🏧",
        "description": "Calculate Fixed Deposit maturity with TDS impact",
        "fields": [
            {"id": "principal", "label": "Deposit Amount", "type": "number", "placeholder": "500000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Interest Rate", "type": "number", "placeholder": "7.5", "min": 1, "max": 15, "suffix": "%", "required": True},
            {"id": "years", "label": "Tenure", "type": "number", "placeholder": "5", "min": 1, "max": 20, "suffix": "years", "required": True},
            {"id": "compounding", "label": "Compounding", "type": "select", "options": [
                {"value": "4", "label": "Quarterly (standard)"},
                {"value": "12", "label": "Monthly"},
                {"value": "1", "label": "Annually"},
            ], "default": "4"},
        ],
        "fn": lambda d: fd_calculator(d["principal"], d["annual_rate"], int(d.get("years", 5)), int(d.get("compounding", 4)), d.get("tax_slab", 30.0)),
        "result_format": [
            {"key": "principal", "label": "Principal", "fmt": "currency"},
            {"key": "maturity_value", "label": "Maturity Value", "fmt": "currency"},
            {"key": "gross_interest", "label": "Gross Interest", "fmt": "currency"},
            {"key": "post_tax_return", "label": "Post-Tax Return (interest)", "fmt": "currency"},
            {"key": "post_tax_maturity", "label": "Post-Tax Maturity Value", "fmt": "currency"},
            {"key": "effective_post_tax_rate", "label": "Effective Post-Tax Rate", "fmt": "pct"},
            {"key": "real_return_after_inflation", "label": "Real Return (after 6% inflation)", "fmt": "pct"},
            {"key": "annual_interest_approx", "label": "Annual Interest (approx)", "fmt": "currency"},
            {"key": "compounding_benefit", "label": "Compounding Benefit", "fmt": "currency"},
            {"key": "tds_applicable", "label": "TDS Applicable", "fmt": "text"},
            {"key": "tds_per_year", "label": "TDS Per Year", "fmt": "currency"},
            {"key": "verdict", "label": "Verdict", "fmt": "text"},
        ],
    },

    "goal_sip": {
        "name": "Goal-Based SIP",
        "icon": "🎯",
        "description": "How much monthly SIP needed to reach a financial goal",
        "fields": [
            {"id": "target_amount", "label": "Target Amount", "type": "number", "placeholder": "10000000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Expected Return", "type": "number", "placeholder": "12", "min": 0, "max": 30, "suffix": "%", "required": True},
            {"id": "years", "label": "Time Horizon", "type": "number", "placeholder": "10", "min": 1, "max": 50, "suffix": "years", "required": True},
        ],
        "fn": lambda d: goal_sip(d["target_amount"], d["annual_rate"], d["years"]),
        "result_format": [
            {"key": "monthly_sip_needed", "label": "Monthly SIP Required", "fmt": "currency"},
            {"key": "total_investment", "label": "Total You'll Invest", "fmt": "currency"},
            {"key": "target_amount", "label": "Target Amount", "fmt": "currency"},
            {"key": "wealth_from_returns", "label": "Wealth from Returns", "fmt": "currency"},
            {"key": "return_multiplier", "label": "Return Multiplier", "fmt": "number"},
        ],
    },

    "stepup_sip": {
        "name": "Step-Up SIP",
        "icon": "📊",
        "description": "SIP with annual increment — grows with your income",
        "fields": [
            {"id": "monthly_sip", "label": "Starting Monthly SIP", "type": "number", "placeholder": "10000", "min": 100, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Expected Return", "type": "number", "placeholder": "12", "min": 0, "max": 30, "suffix": "%", "required": True},
            {"id": "years", "label": "Investment Period", "type": "number", "placeholder": "15", "min": 1, "max": 50, "suffix": "years", "required": True},
            {"id": "step_up_pct", "label": "Annual Step-Up", "type": "number", "placeholder": "10", "min": 0, "max": 50, "suffix": "%", "default": "10"},
        ],
        "fn": lambda d: stepup_sip(d["monthly_sip"], d["annual_rate"], int(d["years"]), d.get("step_up_pct", 10)),
        "result_format": [
            {"key": "total_invested", "label": "Total Invested", "fmt": "currency"},
            {"key": "final_corpus", "label": "Future Value", "fmt": "currency"},
            {"key": "wealth_gained", "label": "Wealth Gained", "fmt": "currency"},
            {"key": "flat_sip_corpus", "label": "Without Step-Up (flat SIP)", "fmt": "currency"},
            {"key": "stepup_advantage", "label": "\u2B06\uFE0F Step-Up Advantage", "fmt": "currency"},
            {"key": "stepup_advantage_pct", "label": "Step-Up Advantage %", "fmt": "pct"},
            {"key": "final_monthly_sip", "label": "Final Monthly SIP", "fmt": "currency"},
        ],
    },

    "fire": {
        "name": "🔥 FIRE Calculator",
        "icon": "🔥",
        "description": "Financial Independence, Retire Early — Lean / Regular / Fat / Barista / Coast FIRE",
        "fields": [
            {"id": "monthly_expenses", "label": "Monthly Expenses", "type": "number", "placeholder": "50000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "current_age", "label": "Current Age", "type": "number", "placeholder": "30", "min": 18, "max": 65, "suffix": "years", "required": True},
            {"id": "retirement_age", "label": "Target Retirement Age", "type": "number", "placeholder": "50", "min": 25, "max": 70, "suffix": "years", "required": True},
            {"id": "current_savings", "label": "Current Savings/Investments", "type": "number", "placeholder": "500000", "min": 0, "suffix": "₹", "default": "0"},
            {"id": "monthly_savings", "label": "Monthly Savings/Investment", "type": "number", "placeholder": "30000", "min": 0, "suffix": "₹", "default": "0"},
            {"id": "expected_return", "label": "Expected Return", "type": "number", "placeholder": "12", "min": 0, "max": 30, "suffix": "%", "default": "12"},
            {"id": "inflation_rate", "label": "Inflation Rate", "type": "number", "placeholder": "6", "min": 0, "max": 15, "suffix": "%", "default": "6"},
            {"id": "coast_fire_age", "label": "Coast FIRE Age (stop investing at)", "type": "number", "placeholder": "40", "min": 0, "max": 65, "suffix": "years", "default": "0"},
        ],
        "fn": lambda d: fire_calculator(d["monthly_expenses"], int(d.get("current_age", 30)), int(d.get("retirement_age", 50)), d.get("current_savings", 0), d.get("monthly_savings", 0), d.get("expected_return", 12), d.get("inflation_rate", 6), int(d.get("coast_fire_age", 0))),
        "result_format": [
            {"key": "annual_expenses_today", "label": "Annual Expenses Today", "fmt": "currency"},
            {"key": "annual_expenses_at_retire", "label": "Annual Expenses at Retirement (inflation-adjusted)", "fmt": "currency"},
            {"key": "lean_fire_corpus", "label": "🟢 Lean FIRE (frugal, ×25 of 60%)", "fmt": "currency", "hint": "Lean FIRE means covering only essential expenses (60% of current spending) with a 4% annual withdrawal. Ideal for extreme frugalists comfortable with a minimalist lifestyle and low-cost living."},
            {"key": "years_to_lean_fire", "label": "   ↳ Years to Lean FIRE", "fmt": "number"},
            {"key": "regular_fire_corpus", "label": "🔵 Regular FIRE (4% rule, ×25)", "fmt": "currency", "hint": "Regular FIRE follows the classic 4% rule — save 25× your annual expenses. Your investments generate enough returns to cover 100% of current lifestyle expenses indefinitely without working."},
            {"key": "years_to_regular_fire", "label": "   ↳ Years to Regular FIRE", "fmt": "number"},
            {"key": "barista_fire_corpus", "label": "☕ Barista FIRE (70% covered, ×33)", "fmt": "currency", "hint": "Barista FIRE means your investments cover ~70% of expenses. You work a low-stress part-time job (like a barista) to cover the remaining 30% and health insurance. Great for those who want some work-life balance without full retirement."},
            {"key": "years_to_barista_fire", "label": "   ↳ Years to Barista FIRE", "fmt": "number"},
            {"key": "fat_fire_corpus", "label": "💎 Fat FIRE (luxury, ×50)", "fmt": "currency", "hint": "Fat FIRE targets a luxurious retirement — 2× regular expenses with a 2% withdrawal rate (50× annual expenses). Provides a large safety margin for premium lifestyle, travel, and unexpected costs."},
            {"key": "years_to_fat_fire", "label": "   ↳ Years to Fat FIRE", "fmt": "number"},
            {"key": "coast_fire_corpus", "label": "🏖️ Coast FIRE (invest once, let it grow)", "fmt": "currency", "hint": "Coast FIRE means you\u2019ve saved enough early that compound growth alone will cover retirement — no more investing needed. You still work to cover current expenses, but can stop saving aggressively."},
            {"key": "sip_needed_for_fire", "label": "Monthly SIP Needed for Regular FIRE", "fmt": "currency"},
            {"key": "post_fire_monthly_income", "label": "Monthly Income at FIRE (4% rule)", "fmt": "currency"},
            {"key": "fire_recommendation", "label": "Recommendation", "fmt": "text"},
        ],
    },

    "capital_gains": {
        "name": "Capital Gains Tax",
        "icon": "📉",
        "description": "Calculate STCG/LTCG tax on stocks, mutual funds, property",
        "fields": [
            {"id": "purchase_price", "label": "Purchase Price", "type": "number", "placeholder": "100000", "min": 0, "suffix": "₹", "required": True},
            {"id": "sale_price", "label": "Sale Price", "type": "number", "placeholder": "200000", "min": 0, "suffix": "₹", "required": True},
            {"id": "holding_months", "label": "Holding Period", "type": "number", "placeholder": "18", "min": 0, "suffix": "months", "required": True},
            {"id": "asset_type", "label": "Asset Type", "type": "select", "options": [
                {"value": "equity", "label": "Equity / Equity MF"},
                {"value": "debt_mf", "label": "Debt Mutual Fund"},
                {"value": "property", "label": "Real Estate"},
                {"value": "gold", "label": "Gold / Gold ETF"},
            ], "default": "equity"},
        ],
        "fn": lambda d: capital_gains_tax(d["purchase_price"], d["sale_price"], int(d["holding_months"]), d.get("asset_type", "equity")),
        "result_format": [
            {"key": "gain", "label": "Capital Gain", "fmt": "currency"},
            {"key": "type", "label": "Gain Type", "fmt": "text"},
            {"key": "effective_tax_rate", "label": "Tax Rate", "fmt": "pct"},
            {"key": "total_tax", "label": "Tax Payable", "fmt": "currency"},
            {"key": "net_gain", "label": "Net Gain (After Tax)", "fmt": "currency"},
            {"key": "in_hand_pct", "label": "In-Hand %", "fmt": "pct"},
            {"key": "holding_tip", "label": "\U0001F4A1 Holding Tip", "fmt": "text"},
        ],
    },

    "inflation_goal": {
        "name": "Inflation Goal Planner",
        "icon": "💸",
        "description": "How much will something cost in the future due to inflation?",
        "fields": [
            {"id": "current_cost", "label": "Current Cost", "type": "number", "placeholder": "500000", "min": 1, "suffix": "₹", "required": True},
            {"id": "years", "label": "Years from Now", "type": "number", "placeholder": "10", "min": 1, "max": 50, "suffix": "years", "required": True},
            {"id": "inflation_rate", "label": "Inflation Rate", "type": "number", "placeholder": "6", "min": 0, "max": 20, "suffix": "%", "default": "6"},
        ],
        "fn": lambda d: inflation_goal_planner(d["current_cost"], int(d["years"]), d.get("inflation_rate", 6)),
        "result_format": [
            {"key": "future_cost", "label": "Future Cost", "fmt": "currency"},
            {"key": "inflation_impact", "label": "Inflation Impact", "fmt": "currency"},
            {"key": "cost_multiplier", "label": "Cost Multiplier", "fmt": "number"},
            {"key": "sip_at_10pct", "label": "Monthly SIP @10%", "fmt": "currency"},
            {"key": "sip_at_12pct", "label": "Monthly SIP @12%", "fmt": "currency"},
            {"key": "sip_at_14pct", "label": "Monthly SIP @14%", "fmt": "currency"},
            {"key": "lumpsum_needed_today", "label": "Lumpsum Needed Today @12%", "fmt": "currency"},
        ],
    },

    "salary_hike": {
        "name": "Salary Hike Analyzer",
        "icon": "📊",
        "description": "Compare CTC growth with different annual hike percentages",
        "fields": [
            {"id": "current_ctc", "label": "Current Annual CTC", "type": "number", "placeholder": "1200000", "min": 100000, "suffix": "₹", "required": True},
        ],
        "fn": lambda d: salary_hike_impact(d["current_ctc"]),
        "result_format": [
            {"key": "current_ctc", "label": "Current CTC", "fmt": "currency"},
            {"key": "current_monthly_takehome", "label": "Current Monthly Take-Home", "fmt": "currency"},
            {"key": "hike_10pct_new_ctc", "label": "10% Hike → New CTC", "fmt": "currency"},
            {"key": "hike_10pct_increase", "label": "   ↳ Take-Home Increase", "fmt": "currency"},
            {"key": "hike_15pct_new_ctc", "label": "15% Hike → New CTC", "fmt": "currency"},
            {"key": "hike_15pct_increase", "label": "   ↳ Take-Home Increase", "fmt": "currency"},
            {"key": "hike_20pct_new_ctc", "label": "20% Hike → New CTC", "fmt": "currency"},
            {"key": "hike_20pct_increase", "label": "   ↳ Take-Home Increase", "fmt": "currency"},
            {"key": "hike_30pct_new_ctc", "label": "30% Hike → New CTC", "fmt": "currency"},
            {"key": "hike_30pct_increase", "label": "   ↳ Take-Home Increase", "fmt": "currency"},
            {"key": "insight", "label": "Insight", "fmt": "text"},
        ],
    },

    "lumpsum_vs_sip": {
        "name": "Lumpsum vs SIP",
        "icon": "⚖️",
        "description": "Compare investing a lump sum vs spreading it via SIP",
        "fields": [
            {"id": "total_amount", "label": "Total Amount to Invest", "type": "number", "placeholder": "1200000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Expected Return", "type": "number", "placeholder": "12", "min": 0, "max": 30, "suffix": "%", "required": True},
            {"id": "years", "label": "Investment Period", "type": "number", "placeholder": "10", "min": 1, "max": 50, "suffix": "years", "required": True},
        ],
        "fn": lambda d: lumpsum_vs_sip(d["total_amount"], d["annual_rate"], d["years"]),
        "result_format": [
            {"key": "lumpsum_value", "label": "Lumpsum Future Value", "fmt": "currency"},
            {"key": "lumpsum_return_pct", "label": "Lumpsum Return %", "fmt": "pct"},
            {"key": "sip_monthly", "label": "Equivalent Monthly SIP", "fmt": "currency"},
            {"key": "sip_value", "label": "SIP Future Value", "fmt": "currency"},
            {"key": "sip_return_pct", "label": "SIP Return %", "fmt": "pct"},
            {"key": "lumpsum_advantage", "label": "Lumpsum Advantage", "fmt": "currency"},
            {"key": "verdict", "label": "Verdict", "fmt": "text"},
        ],
    },

    "education_loan": {
        "name": "Education Loan",
        "icon": "🎓",
        "description": "Calculate education loan EMI with moratorium period",
        "fields": [
            {"id": "loan_amount", "label": "Loan Amount", "type": "number", "placeholder": "2000000", "min": 10000, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Interest Rate", "type": "number", "placeholder": "9", "min": 0, "max": 20, "suffix": "%", "required": True},
            {"id": "tenure_years", "label": "Repayment Period", "type": "number", "placeholder": "7", "min": 1, "max": 15, "suffix": "years", "required": True},
            {"id": "moratorium_months", "label": "Moratorium Period", "type": "number", "placeholder": "12", "min": 0, "max": 60, "suffix": "months", "default": "12"},
        ],
        "fn": lambda d: education_loan_calc(d["loan_amount"], d["annual_rate"], d["tenure_years"], int(d.get("moratorium_months", 12))),
        "result_format": [
            {"key": "emi", "label": "Monthly EMI", "fmt": "currency"},
            {"key": "total_payment", "label": "Total Payment", "fmt": "currency"},
            {"key": "total_interest", "label": "Total Interest", "fmt": "currency"},
            {"key": "moratorium_interest", "label": "Interest During Moratorium", "fmt": "currency"},
            {"key": "effective_principal", "label": "Loan After Moratorium", "fmt": "currency"},
            {"key": "section_80e_deduction_total", "label": "\U0001F4B0 80E Tax Deduction", "fmt": "currency"},
            {"key": "estimated_tax_saved_80e", "label": "Tax Saved via 80E", "fmt": "currency"},
            {"key": "effective_cost_after_tax", "label": "Effective Interest Cost", "fmt": "currency"},
            {"key": "effective_rate_after_tax", "label": "Effective Rate After Tax (%)", "fmt": "pct"},
            {"key": "min_income_for_emi", "label": "Min Income for EMI (30% rule)", "fmt": "currency"},
        ],
    },

    "hra": {
        "name": "HRA Exemption",
        "icon": "🏘️",
        "description": "Calculate HRA tax exemption — metro vs non-metro",
        "fields": [
            {"id": "basic_annual", "label": "Annual Basic Salary", "type": "number", "placeholder": "600000", "min": 0, "suffix": "₹", "required": True},
            {"id": "hra_received", "label": "Annual HRA Received", "type": "number", "placeholder": "300000", "min": 0, "suffix": "₹", "required": True},
            {"id": "rent_paid", "label": "Annual Rent Paid", "type": "number", "placeholder": "240000", "min": 0, "suffix": "₹", "required": True},
            {"id": "metro", "label": "City Type", "type": "select", "options": [
                {"value": "true", "label": "Metro (Delhi, Mumbai, Chennai, Kolkata)"},
                {"value": "false", "label": "Non-Metro"},
            ], "default": "true"},
        ],
        "fn": lambda d: hra_exemption(d["basic_annual"], d["hra_received"], d["rent_paid"], d.get("metro", "true") == "true"),
        "result_format": [
            {"key": "hra_exemption", "label": "\u2705 HRA Exemption", "fmt": "currency"},
            {"key": "exemption_rule", "label": "Limiting Rule", "fmt": "text"},
            {"key": "option1_actual_hra", "label": "Rule 1: Actual HRA", "fmt": "currency"},
            {"key": "option2_rent_minus_10pct", "label": "Rule 2: Rent - 10% Basic", "fmt": "currency"},
            {"key": "option3_50_or_40_pct_basic", "label": "Rule 3: 50%/40% of Basic", "fmt": "currency"},
            {"key": "taxable_hra", "label": "Taxable HRA", "fmt": "currency"},
            {"key": "annual_tax_saving_approx", "label": "Annual Tax Saving", "fmt": "currency"},
            {"key": "monthly_tax_saving", "label": "Monthly Tax Saving", "fmt": "currency"},
            {"key": "optimal_rent", "label": "\U0001F4A1 Optimal Annual Rent", "fmt": "currency"},
        ],
    },

    "loan_prepay": {
        "name": "Loan Prepayment",
        "icon": "⚡",
        "description": "Impact of extra payments — reduce tenure or EMI",
        "fields": [
            {"id": "principal", "label": "Outstanding Loan Amount", "type": "number", "placeholder": "3000000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Interest Rate", "type": "number", "placeholder": "8.5", "min": 0, "max": 30, "suffix": "%", "required": True},
            {"id": "remaining_months", "label": "Remaining Tenure", "type": "number", "placeholder": "180", "min": 1, "max": 480, "suffix": "months", "required": True},
            {"id": "prepay_amount", "label": "Prepayment Amount", "type": "number", "placeholder": "500000", "min": 0, "suffix": "₹", "required": True},
            {"id": "strategy", "label": "Prepayment Strategy", "type": "select", "options": [
                {"value": "reduce_tenure", "label": "Reduce Tenure (keep EMI)"},
                {"value": "reduce_emi", "label": "Reduce EMI (keep tenure)"},
            ], "default": "reduce_tenure"},
        ],
        "fn": lambda d: loan_prepayment(d["principal"], d["annual_rate"], int(d["remaining_months"]), d["prepay_amount"], reduce=d.get("strategy", "reduce_tenure").replace("reduce_", "")),
        "result_format": [
            {"key": "original_emi", "label": "Original EMI", "fmt": "currency"},
            {"key": "original_tenure_months", "label": "Original Tenure", "fmt": "number", "suffix": " months"},
            {"key": "original_total_interest", "label": "Total Interest (Without Prepayment)", "fmt": "currency"},
            {"key": "original_total_cost", "label": "Total Cost (Without Prepayment)", "fmt": "currency"},
            {"key": "prepay_amount", "label": "Prepayment Amount", "fmt": "currency"},
            {"key": "new_emi", "label": "New EMI (After Prepayment)", "fmt": "currency"},
            {"key": "new_total_tenure", "label": "New Total Tenure", "fmt": "number", "suffix": " months"},
            {"key": "new_total_interest", "label": "Total Interest (With Prepayment)", "fmt": "currency"},
            {"key": "total_new_cost", "label": "Total Cost (With Prepayment)", "fmt": "currency"},
            {"key": "months_saved", "label": "Months Saved", "fmt": "number"},
            {"key": "years_saved", "label": "Years Saved", "fmt": "number"},
            {"key": "interest_saved", "label": "Interest Saved", "fmt": "currency"},
            {"key": "interest_saved_pct", "label": "Interest Saved %", "fmt": "pct"},
        ],
    },

    # ──────────────────── Groww-style Calculators ────────────────────

    "rd": {
        "name": "RD Calculator",
        "icon": "🔄",
        "description": "Recurring Deposit — monthly deposits with quarterly compounding",
        "fields": [
            {"id": "monthly_deposit", "label": "Monthly Deposit", "type": "number", "placeholder": "5000", "min": 100, "suffix": "₹", "required": True},
            {"id": "annual_rate", "label": "Interest Rate", "type": "number", "placeholder": "6.5", "min": 1, "max": 15, "suffix": "%", "required": True},
            {"id": "years", "label": "Tenure", "type": "number", "placeholder": "5", "min": 1, "max": 10, "suffix": "years", "required": True},
        ],
        "fn": lambda d: rd_calculator(d["monthly_deposit"], d["annual_rate"], int(d["years"])),
        "result_format": [
            {"key": "total_invested", "label": "Total Invested", "fmt": "currency"},
            {"key": "maturity_value", "label": "Maturity Value", "fmt": "currency"},
            {"key": "total_interest", "label": "Interest Earned", "fmt": "currency"},
            {"key": "effective_yield_pct", "label": "Effective Yield", "fmt": "pct"},
            {"key": "wealth_multiplier", "label": "Wealth Multiplier", "fmt": "number"},
            {"key": "monthly_interest_approx", "label": "Monthly Interest (approx)", "fmt": "currency"},
            {"key": "sip_mf_comparison", "label": "SIP MF Value (same rate)", "fmt": "currency"},
            {"key": "sip_advantage_over_rd", "label": "SIP Advantage over RD", "fmt": "currency"},
        ],
    },

    "ssy": {
        "name": "SSY Calculator",
        "icon": "👧",
        "description": "Sukanya Samriddhi Yojana — savings scheme for girl child (8.2% rate)",
        "fields": [
            {"id": "annual_deposit", "label": "Annual Deposit", "type": "number", "placeholder": "150000", "min": 250, "max": 150000, "suffix": "₹", "required": True},
            {"id": "girl_age", "label": "Girl's Current Age", "type": "number", "placeholder": "5", "min": 0, "max": 10, "suffix": "years", "required": True},
            {"id": "current_rate", "label": "Interest Rate", "type": "number", "placeholder": "8.2", "min": 1, "max": 15, "suffix": "%", "default": "8.2"},
        ],
        "fn": lambda d: ssy_calculator(d["annual_deposit"], int(d["girl_age"]), d.get("current_rate", 8.2)),
        "result_format": [
            {"key": "total_deposited", "label": "Total Deposited (15 years)", "fmt": "currency"},
            {"key": "total_interest", "label": "Interest Earned", "fmt": "currency"},
            {"key": "maturity_value", "label": "Maturity Value", "fmt": "currency"},
            {"key": "wealth_multiplier", "label": "Wealth Multiplier", "fmt": "number"},
            {"key": "tax_benefit_80c", "label": "Annual 80C Benefit", "fmt": "currency"},
            {"key": "maturity_years", "label": "Account Matures In", "fmt": "number"},
            {"key": "girl_age_at_maturity", "label": "Girl's Age at Maturity", "fmt": "number"},
            {"key": "partial_withdrawal_after_year", "label": "Partial Withdrawal After Year", "fmt": "number"},
        ],
    },

    "nps": {
        "name": "NPS Calculator",
        "icon": "🏛️",
        "description": "National Pension System — retirement corpus with annuity",
        "fields": [
            {"id": "monthly_contribution", "label": "Monthly Contribution", "type": "number", "placeholder": "5000", "min": 500, "suffix": "₹", "required": True},
            {"id": "current_age", "label": "Current Age", "type": "number", "placeholder": "30", "min": 18, "max": 59, "suffix": "years", "required": True},
            {"id": "expected_return", "label": "Expected Return", "type": "number", "placeholder": "10", "min": 1, "max": 20, "suffix": "%", "default": "10"},
            {"id": "annuity_pct", "label": "Annuity Purchase %", "type": "number", "placeholder": "40", "min": 40, "max": 100, "suffix": "%", "default": "40"},
        ],
        "fn": lambda d: nps_calculator(d["monthly_contribution"], int(d["current_age"]), d.get("expected_return", 10), d.get("annuity_pct", 40)),
        "result_format": [
            {"key": "total_invested", "label": "Total Invested", "fmt": "currency"},
            {"key": "total_corpus", "label": "Total Corpus at 60", "fmt": "currency"},
            {"key": "wealth_multiplier", "label": "Wealth Multiplier", "fmt": "number"},
            {"key": "lump_sum_withdrawal", "label": "Lump Sum (tax-free 60%)", "fmt": "currency"},
            {"key": "annuity_investment", "label": "Annuity Purchase (40%)", "fmt": "currency"},
            {"key": "est_monthly_pension", "label": "Est. Monthly Pension", "fmt": "currency"},
            {"key": "annual_tax_saved", "label": "Annual Tax Saved (80CCD)", "fmt": "currency"},
            {"key": "total_tax_saved_lifetime", "label": "Total Tax Saved (lifetime)", "fmt": "currency"},
        ],
    },

    "swp": {
        "name": "SWP Calculator",
        "icon": "💳",
        "description": "Systematic Withdrawal Plan — regular income from lump sum investment",
        "fields": [
            {"id": "total_investment", "label": "Total Investment", "type": "number", "placeholder": "500000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "withdrawal_per_month", "label": "Monthly Withdrawal", "type": "number", "placeholder": "10000", "min": 100, "suffix": "₹", "required": True},
            {"id": "expected_return", "label": "Expected Return", "type": "number", "placeholder": "8", "min": 0, "max": 30, "suffix": "%", "default": "8"},
            {"id": "years", "label": "Time Period", "type": "number", "placeholder": "5", "min": 1, "max": 30, "suffix": "years", "required": True},
        ],
        "fn": lambda d: swp_calculator(d["total_investment"], d["withdrawal_per_month"], d.get("expected_return", 8), int(d["years"])),
        "result_format": [
            {"key": "total_investment", "label": "Total Investment", "fmt": "currency"},
            {"key": "total_withdrawn", "label": "Total Withdrawn", "fmt": "currency"},
            {"key": "final_value", "label": "Remaining Corpus", "fmt": "currency"},
            {"key": "total_earnings", "label": "Total Earnings", "fmt": "currency"},
            {"key": "effective_return", "label": "Effective Return %", "fmt": "pct"},
            {"key": "sustainable_withdrawal", "label": "\U0001F4A1 Max Sustainable Monthly", "fmt": "currency"},
            {"key": "corpus_lasted_months", "label": "Corpus Lasted", "fmt": "number"},
        ],
    },

    "nsc": {
        "name": "NSC Calculator",
        "icon": "📜",
        "description": "National Savings Certificate — 5-year lock-in, 80C tax benefit",
        "fields": [
            {"id": "investment_amount", "label": "Investment Amount", "type": "number", "placeholder": "100000", "min": 100, "suffix": "₹", "required": True},
            {"id": "interest_rate", "label": "Interest Rate", "type": "number", "placeholder": "7.7", "min": 1, "max": 15, "suffix": "%", "default": "7.7"},
        ],
        "fn": lambda d: nsc_calculator(d["investment_amount"], d.get("interest_rate", 7.7)),
        "result_format": [
            {"key": "investment_amount", "label": "Investment", "fmt": "currency"},
            {"key": "maturity_value", "label": "Maturity Value (5 years)", "fmt": "currency"},
            {"key": "total_interest", "label": "Interest Earned", "fmt": "currency"},
            {"key": "tax_benefit_80c", "label": "Tax Benefit (80C)", "fmt": "currency"},
        ],
    },

    "gratuity": {
        "name": "Gratuity Calculator",
        "icon": "🎖️",
        "description": "Calculate gratuity payout as per Payment of Gratuity Act",
        "fields": [
            {"id": "basic_salary_monthly", "label": "Last Drawn Basic + DA (Monthly)", "type": "number", "placeholder": "60000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "years_of_service", "label": "Years of Service", "type": "number", "placeholder": "20", "min": 5, "max": 50, "suffix": "years", "required": True},
        ],
        "fn": lambda d: gratuity_calculator(d["basic_salary_monthly"], d["years_of_service"]),
        "result_format": [
            {"key": "gratuity_amount", "label": "Gratuity Payable", "fmt": "currency"},
            {"key": "net_gratuity", "label": "Net Gratuity (After Tax)", "fmt": "currency"},
            {"key": "tax_exempt_amount", "label": "Tax Exempt Amount", "fmt": "currency"},
            {"key": "taxable_amount", "label": "Taxable Amount", "fmt": "currency"},
            {"key": "tax_on_gratuity", "label": "Tax on Gratuity", "fmt": "currency"},
            {"key": "years_of_service", "label": "Service Years (rounded)", "fmt": "number"},
            {"key": "monthly_equivalent", "label": "Monthly Equivalent", "fmt": "currency"},
            {"key": "gratuity_at_10yr", "label": "Gratuity at 10 Years", "fmt": "currency"},
            {"key": "gratuity_at_20yr", "label": "Gratuity at 20 Years", "fmt": "currency"},
            {"key": "gratuity_at_30yr", "label": "Gratuity at 30 Years", "fmt": "currency"},
        ],
    },

    "epf": {
        "name": "EPF Calculator",
        "icon": "🏗️",
        "description": "Employee Provident Fund — retirement savings with employer match",
        "fields": [
            {"id": "basic_salary_monthly", "label": "Monthly Basic + DA", "type": "number", "placeholder": "50000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "current_age", "label": "Current Age", "type": "number", "placeholder": "30", "min": 18, "max": 57, "suffix": "years", "required": True},
            {"id": "employee_contribution_pct", "label": "Employee Contribution", "type": "number", "placeholder": "12", "min": 12, "max": 100, "suffix": "%", "default": "12"},
            {"id": "annual_salary_hike_pct", "label": "Annual Salary Hike", "type": "number", "placeholder": "5", "min": 0, "max": 30, "suffix": "%", "default": "5"},
            {"id": "epf_rate", "label": "EPF Interest Rate", "type": "number", "placeholder": "8.25", "min": 1, "max": 15, "suffix": "%", "default": "8.25"},
        ],
        "fn": lambda d: epf_calculator(d["basic_salary_monthly"], int(d["current_age"]), d.get("employee_contribution_pct", 12), 12.0, d.get("annual_salary_hike_pct", 5), d.get("epf_rate", 8.25)),
        "result_format": [
            {"key": "total_employee_contribution", "label": "Your Contribution", "fmt": "currency"},
            {"key": "total_employer_contribution", "label": "Employer Contribution", "fmt": "currency"},
            {"key": "total_contributions", "label": "Total Contributions", "fmt": "currency"},
            {"key": "total_interest_earned", "label": "Interest Earned", "fmt": "currency"},
            {"key": "maturity_value", "label": "Total EPF at 58", "fmt": "currency"},
            {"key": "wealth_multiplier", "label": "Wealth Multiplier", "fmt": "number"},
            {"key": "est_monthly_pension", "label": "Est. Monthly Pension (8% annuity)", "fmt": "currency"},
            {"key": "final_basic_salary", "label": "Final Basic Salary at 58", "fmt": "currency"},
        ],
    },

    "scss": {
        "name": "SCSS Calculator",
        "icon": "👴",
        "description": "Senior Citizens Savings Scheme — 8.2% quarterly payout, 5-year tenure",
        "fields": [
            {"id": "investment_amount", "label": "Investment Amount", "type": "number", "placeholder": "500000", "min": 1000, "max": 3000000, "suffix": "₹", "required": True},
            {"id": "interest_rate", "label": "Interest Rate", "type": "number", "placeholder": "8.2", "min": 1, "max": 15, "suffix": "%", "default": "8.2"},
        ],
        "fn": lambda d: scss_calculator(d["investment_amount"], d.get("interest_rate", 8.2)),
        "result_format": [
            {"key": "quarterly_interest", "label": "Quarterly Income", "fmt": "currency"},
            {"key": "annual_income", "label": "Annual Income", "fmt": "currency"},
            {"key": "total_interest", "label": "Total Interest (5 years)", "fmt": "currency"},
            {"key": "maturity_value", "label": "Maturity Value", "fmt": "currency"},
        ],
    },

    "pomis": {
        "name": "Post Office MIS",
        "icon": "🏤",
        "description": "Post Office Monthly Income Scheme — guaranteed monthly income",
        "fields": [
            {"id": "investment_amount", "label": "Investment Amount", "type": "number", "placeholder": "900000", "min": 1000, "max": 900000, "suffix": "₹", "required": True},
            {"id": "interest_rate", "label": "Interest Rate", "type": "number", "placeholder": "7.4", "min": 1, "max": 15, "suffix": "%", "default": "7.4"},
        ],
        "fn": lambda d: post_office_mis_calculator(d["investment_amount"], d.get("interest_rate", 7.4)),
        "result_format": [
            {"key": "monthly_income", "label": "Monthly Income", "fmt": "currency"},
            {"key": "annual_income", "label": "Annual Income", "fmt": "currency"},
            {"key": "total_interest", "label": "Total Interest (5 years)", "fmt": "currency"},
            {"key": "maturity_value", "label": "Principal Returned", "fmt": "currency"},
        ],
    },

    "apy": {
        "name": "APY Calculator",
        "icon": "🛡️",
        "description": "Atal Pension Yojana — guaranteed pension of ₹1K-5K/month after 60",
        "fields": [
            {"id": "monthly_contribution", "label": "Monthly Contribution", "type": "number", "placeholder": "1000", "min": 42, "max": 5000, "suffix": "₹", "required": True},
            {"id": "current_age", "label": "Current Age", "type": "number", "placeholder": "25", "min": 18, "max": 40, "suffix": "years", "required": True},
            {"id": "desired_pension", "label": "Desired Monthly Pension", "type": "select", "options": [
                {"value": "1000", "label": "₹1,000/month"},
                {"value": "2000", "label": "₹2,000/month"},
                {"value": "3000", "label": "₹3,000/month"},
                {"value": "4000", "label": "₹4,000/month"},
                {"value": "5000", "label": "₹5,000/month"},
            ], "default": "5000"},
        ],
        "fn": lambda d: apy_calculator(d["monthly_contribution"], int(d["current_age"]), float(d.get("desired_pension", 5000))),
        "result_format": [
            {"key": "total_invested", "label": "Total Invested", "fmt": "currency"},
            {"key": "monthly_pension_at_60", "label": "Monthly Pension at 60", "fmt": "currency"},
            {"key": "estimated_corpus", "label": "Estimated Corpus", "fmt": "currency"},
            {"key": "spouse_pension", "label": "Spouse Pension", "fmt": "currency"},
        ],
    },

    "gst": {
        "name": "GST Calculator",
        "icon": "🧾",
        "description": "Calculate GST amount, CGST, SGST from pre/post-tax amount",
        "fields": [
            {"id": "amount", "label": "Amount", "type": "number", "placeholder": "100000", "min": 0, "suffix": "₹", "required": True},
            {"id": "gst_rate", "label": "GST Rate", "type": "select", "options": [
                {"value": "5", "label": "5%"},
                {"value": "12", "label": "12%"},
                {"value": "18", "label": "18%"},
                {"value": "28", "label": "28%"},
            ], "default": "18"},
            {"id": "is_inclusive", "label": "Amount Type", "type": "select", "options": [
                {"value": "false", "label": "Exclusive (add GST)"},
                {"value": "true", "label": "Inclusive (GST included)"},
            ], "default": "false"},
        ],
        "fn": lambda d: gst_calculator(d["amount"], float(d.get("gst_rate", 18)), d.get("is_inclusive", "false") == "true"),
        "result_format": [
            {"key": "base_amount", "label": "Base Amount", "fmt": "currency"},
            {"key": "gst_amount", "label": "GST Amount", "fmt": "currency"},
            {"key": "cgst", "label": "CGST", "fmt": "currency"},
            {"key": "sgst", "label": "SGST", "fmt": "currency"},
            {"key": "total_amount", "label": "Total Amount", "fmt": "currency"},
        ],
    },

    "tds": {
        "name": "TDS Calculator",
        "icon": "📋",
        "description": "Tax Deducted at Source — for salary, rent, interest, etc.",
        "fields": [
            {"id": "income", "label": "Income / Payment Amount", "type": "number", "placeholder": "500000", "min": 0, "suffix": "₹", "required": True},
            {"id": "income_type", "label": "Income Type", "type": "select", "options": [
                {"value": "salary", "label": "Salary"},
                {"value": "interest", "label": "Interest (FD/RD)"},
                {"value": "rent", "label": "Rent"},
                {"value": "professional_fees", "label": "Professional Fees"},
                {"value": "commission", "label": "Commission"},
                {"value": "dividend", "label": "Dividend"},
                {"value": "lottery", "label": "Lottery / Game Show"},
                {"value": "property_sale", "label": "Property Sale"},
            ], "default": "salary"},
            {"id": "pan_available", "label": "PAN Available?", "type": "select", "options": [
                {"value": "true", "label": "Yes"},
                {"value": "false", "label": "No (higher TDS)"},
            ], "default": "true"},
        ],
        "fn": lambda d: tds_calculator(d["income"], d.get("income_type", "salary"), d.get("pan_available", "true") == "true"),
        "result_format": [
            {"key": "income", "label": "Gross Income", "fmt": "currency"},
            {"key": "tds_rate_pct", "label": "TDS Rate", "fmt": "pct"},
            {"key": "tds_amount", "label": "TDS Deducted", "fmt": "currency"},
            {"key": "net_amount", "label": "Net Amount", "fmt": "currency"},
        ],
    },

    "simple_interest": {
        "name": "Simple Interest",
        "icon": "📐",
        "description": "Calculate simple interest on investments or loans",
        "fields": [
            {"id": "principal", "label": "Principal Amount", "type": "number", "placeholder": "100000", "min": 1, "suffix": "₹", "required": True},
            {"id": "rate", "label": "Annual Interest Rate", "type": "number", "placeholder": "8", "min": 0, "max": 50, "suffix": "%", "required": True},
            {"id": "years", "label": "Time Period", "type": "number", "placeholder": "5", "min": 1, "max": 50, "suffix": "years", "required": True},
        ],
        "fn": lambda d: simple_interest(d["principal"], d["rate"], d["years"]),
        "result_format": [
            {"key": "principal", "label": "Principal", "fmt": "currency"},
            {"key": "interest", "label": "Interest Earned", "fmt": "currency"},
            {"key": "total_amount", "label": "Total Amount", "fmt": "currency"},
        ],
    },

    "flat_vs_reducing": {
        "name": "Flat vs Reducing Rate",
        "icon": "⚖️",
        "description": "Compare flat rate vs reducing balance EMI for loans",
        "fields": [
            {"id": "principal", "label": "Loan Amount", "type": "number", "placeholder": "500000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "flat_rate", "label": "Flat Interest Rate", "type": "number", "placeholder": "10", "min": 0, "max": 40, "suffix": "%", "required": True},
            {"id": "reducing_rate", "label": "Reducing Balance Rate", "type": "number", "placeholder": "18", "min": 0, "max": 40, "suffix": "%", "required": True},
            {"id": "tenure_months", "label": "Loan Tenure", "type": "number", "placeholder": "36", "min": 1, "max": 360, "suffix": "months", "required": True},
        ],
        "fn": lambda d: flat_vs_reducing_rate(d["principal"], d["flat_rate"], d["reducing_rate"], int(d["tenure_months"])),
        "result_format": [
            {"key": "flat_emi", "label": "Flat Rate EMI", "fmt": "currency"},
            {"key": "flat_total_interest", "label": "Flat Total Interest", "fmt": "currency"},
            {"key": "reducing_emi", "label": "Reducing Rate EMI", "fmt": "currency"},
            {"key": "reducing_total_interest", "label": "Reducing Total Interest", "fmt": "currency"},
            {"key": "savings_with_reducing", "label": "Savings", "fmt": "currency"},
            {"key": "better_option", "label": "Better Option", "fmt": "text"},
        ],
    },

    "kvp": {
        "name": "KVP Calculator",
        "icon": "🌾",
        "description": "Kisan Vikas Patra — doubles your money at guaranteed rate",
        "fields": [
            {"id": "investment_amount", "label": "Investment Amount", "type": "number", "placeholder": "100000", "min": 1000, "suffix": "₹", "required": True},
            {"id": "interest_rate", "label": "Interest Rate", "type": "number", "placeholder": "7.5", "min": 1, "max": 15, "suffix": "%", "default": "7.5"},
        ],
        "fn": lambda d: kvp_calculator(d["investment_amount"], d.get("interest_rate", 7.5)),
        "result_format": [
            {"key": "investment_amount", "label": "Investment", "fmt": "currency"},
            {"key": "maturity_value", "label": "Maturity Value (2x)", "fmt": "currency"},
            {"key": "total_interest", "label": "Interest Earned", "fmt": "currency"},
            {"key": "months_to_double", "label": "Months to Double", "fmt": "number"},
        ],
    },

    "mf_returns": {
        "name": "Mutual Fund Returns",
        "icon": "📊",
        "description": "MF returns with expense ratio impact — SIP or Lumpsum",
        "fields": [
            {"id": "investment_amount", "label": "Investment Amount", "type": "number", "placeholder": "10000", "min": 100, "suffix": "₹", "required": True},
            {"id": "annual_return", "label": "Expected Annual Return", "type": "number", "placeholder": "12", "min": 0, "max": 30, "suffix": "%", "required": True},
            {"id": "years", "label": "Investment Period", "type": "number", "placeholder": "10", "min": 1, "max": 40, "suffix": "years", "required": True},
            {"id": "expense_ratio", "label": "Expense Ratio", "type": "number", "placeholder": "1.5", "min": 0, "max": 5, "suffix": "%", "default": "1.5"},
            {"id": "is_sip", "label": "Investment Mode", "type": "select", "options": [
                {"value": "true", "label": "SIP (monthly)"},
                {"value": "false", "label": "Lumpsum (one-time)"},
            ], "default": "true"},
        ],
        "fn": lambda d: mutual_fund_returns(d["investment_amount"], d["annual_return"], int(d["years"]), d.get("expense_ratio", 1.5), d.get("is_sip", "true") == "true"),
        "result_format": [
            {"key": "total_invested", "label": "Total Invested", "fmt": "currency"},
            {"key": "future_value", "label": "Future Value", "fmt": "currency"},
            {"key": "wealth_gained", "label": "Wealth Gained", "fmt": "currency"},
            {"key": "expense_ratio_impact", "label": "Expense Ratio Cost", "fmt": "currency"},
        ],
    },

    "xirr": {
        "name": "XIRR Calculator",
        "icon": "📐",
        "description": "Extended Internal Rate of Return — annualized return for SIP/irregular investments",
        "fields": [
            {"id": "sip_amount", "label": "SIP / Recurring Amount", "type": "number", "placeholder": "10000", "min": 100, "suffix": "₹", "required": True},
            {"id": "num_months", "label": "Number of Months", "type": "number", "placeholder": "36", "min": 1, "max": 600, "suffix": "months", "required": True},
            {"id": "maturity_value", "label": "Total Maturity Value", "type": "number", "placeholder": "500000", "min": 1, "suffix": "₹", "required": True},
        ],
        "fn": lambda d: xirr_sip_calculator(d["sip_amount"], int(d["num_months"]), d["maturity_value"]),
        "result_format": [
            {"key": "xirr_pct", "label": "XIRR (Annualized Return)", "fmt": "pct"},
            {"key": "total_invested", "label": "Total Invested", "fmt": "currency"},
            {"key": "maturity_value", "label": "Maturity Value", "fmt": "currency"},
            {"key": "net_gain", "label": "Net Gain", "fmt": "currency"},
            {"key": "absolute_return_pct", "label": "Absolute Return", "fmt": "pct"},
        ],
    },
}


# ──────────────────────── Calculator Result Cache ────────────────────────
import hashlib
import json as _json
import time as _time
import threading as _threading

_calc_cache: dict[str, tuple[float, dict]] = {}  # key -> (timestamp, result)
_CALC_CACHE_TTL = 300  # 5 minutes — pure functions, but allows param tuning
_CALC_CACHE_MAX = 256  # max entries to prevent unbounded growth
_calc_cache_lock = _threading.Lock()


def _calc_cache_key(calc_id: str, inputs: dict) -> str:
    """Generate a deterministic cache key from calculator id + inputs."""
    # Sort keys for deterministic hashing
    canonical = _json.dumps({"c": calc_id, "i": inputs}, sort_keys=True, default=str)
    return hashlib.md5(canonical.encode()).hexdigest()


def _evict_stale_cache():
    """Remove expired entries and enforce max size."""
    now = _time.time()
    expired = [k for k, (ts, _) in _calc_cache.items() if now - ts > _CALC_CACHE_TTL]
    for k in expired:
        del _calc_cache[k]
    # If still over limit, remove oldest entries
    if len(_calc_cache) > _CALC_CACHE_MAX:
        sorted_keys = sorted(_calc_cache, key=lambda k: _calc_cache[k][0])
        for k in sorted_keys[:len(_calc_cache) - _CALC_CACHE_MAX]:
            del _calc_cache[k]


# ──────────────────────── Calculator Execution ────────────────────────

def run_calculator(calc_id: str, inputs: dict) -> dict:
    """Run a calculator with validated inputs, return structured result.
    Results are cached for 5 minutes (pure functions, same inputs = same output)."""
    if calc_id not in CALCULATORS:
        return {"error": f"Unknown calculator: {calc_id}"}

    # Check cache first
    cache_key = _calc_cache_key(calc_id, inputs)
    with _calc_cache_lock:
        if cache_key in _calc_cache:
            ts, cached_result = _calc_cache[cache_key]
            if _time.time() - ts < _CALC_CACHE_TTL:
                cached_result["_cached"] = True
                return cached_result
            else:
                del _calc_cache[cache_key]

    calc = CALCULATORS[calc_id]

    # Validate and cast inputs
    processed = {}
    errors = []
    for field in calc["fields"]:
        fid = field["id"]
        raw = inputs.get(fid, field.get("default"))

        if raw is None or raw == "":
            if field.get("required"):
                errors.append(f"{field['label']} is required")
            continue

        try:
            if field["type"] == "number":
                val = float(raw)
                if "min" in field and val < field["min"]:
                    errors.append(f"{field['label']} must be at least {field['min']}")
                if "max" in field and val > field["max"]:
                    errors.append(f"{field['label']} must be at most {field['max']}")
                processed[fid] = val
            elif field["type"] == "select":
                processed[fid] = str(raw)
            else:
                processed[fid] = raw
        except (ValueError, TypeError):
            errors.append(f"{field['label']}: invalid value '{raw}'")

    if errors:
        return {"error": "; ".join(errors)}

    # Special handling for tax comparison
    if calc["fn"] == "_tax_compare":
        result = _tax_compare(processed)
        if "error" not in result:
            with _calc_cache_lock:
                _evict_stale_cache()
                _calc_cache[cache_key] = (_time.time(), result)
        return result

    try:
        result = calc["fn"](processed)
        if isinstance(result, dict) and "error" in result:
            return {"error": result["error"]}
        output = {
            "calculator": calc_id,
            "name": calc["name"],
            "icon": calc["icon"],
            "result": result,
            "format": calc["result_format"],
        }
        # Cache successful results
        with _calc_cache_lock:
            _evict_stale_cache()
            _calc_cache[cache_key] = (_time.time(), output)
        return output
    except Exception as e:
        return {"error": f"Calculation error: {str(e)}"}


def _tax_compare(inputs: dict) -> dict:
    """Handle tax regime comparison."""
    income = inputs["taxable_income"]
    regime = inputs.get("regime", "both")

    if regime == "both":
        new_res = tax_bracket_india(income, "new")
        old_res = tax_bracket_india(income, "old")
        better = "New Regime" if new_res["total_tax"] <= old_res["total_tax"] else "Old Regime"
        savings = abs(new_res["total_tax"] - old_res["total_tax"])
        return {
            "calculator": "tax_india",
            "name": "Income Tax Comparison",
            "icon": "🏛️",
            "result": {
                "new_regime": new_res,
                "old_regime": old_res,
                "better_regime": better,
                "tax_savings": savings,
            },
            "format": [
                {"key": "new_regime.total_tax", "label": "Tax (New Regime)", "fmt": "currency"},
                {"key": "new_regime.effective_rate", "label": "Effective Rate (New)", "fmt": "pct"},
                {"key": "old_regime.total_tax", "label": "Tax (Old Regime)", "fmt": "currency"},
                {"key": "old_regime.effective_rate", "label": "Effective Rate (Old)", "fmt": "pct"},
                {"key": "better_regime", "label": "Better Regime", "fmt": "text"},
                {"key": "tax_savings", "label": "You Save", "fmt": "currency"},
            ],
        }
    else:
        res = tax_bracket_india(income, regime)
        return {
            "calculator": "tax_india",
            "name": f"Income Tax ({regime.title()} Regime)",
            "icon": "🏛️",
            "result": res,
            "format": [
                {"key": "taxable_income", "label": "Taxable Income", "fmt": "currency"},
                {"key": "total_tax", "label": "Total Tax", "fmt": "currency"},
                {"key": "effective_rate", "label": "Effective Rate", "fmt": "pct"},
                {"key": "rebate_87a", "label": "Rebate u/s 87A", "fmt": "text"},
            ],
        }


def list_calculators() -> list:
    """Return list of available calculators with metadata (no functions)."""
    return [
        {
            "id": k,
            "name": v["name"],
            "icon": v["icon"],
            "description": v["description"],
            "fields": v["fields"],
        }
        for k, v in CALCULATORS.items()
    ]
