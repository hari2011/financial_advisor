"""
Indian Financial Knowledge Base.

Comprehensive reference data for Indian personal finance — salary structures,
tax calculations, EPF/gratuity rules, investment vehicles, and formulas.

Injected into LLM context so the model can REASON about Indian finance
rather than just copying pre-computed numbers.
"""

import re

# ─────────────────────── Knowledge Sections ───────────────────────

SECTIONS = {}

# ──────── CTC TO TAKE-HOME COMPLETE PIPELINE ────────
SECTIONS["ctc_to_takehome"] = """
CTC TO TAKE-HOME — STEP-BY-STEP CALCULATION:

CTC = Gross Salary + Employer EPF + Gratuity Provision

STEP 1 — SPLIT CTC INTO COMPONENTS:
  Basic = CTC × 50% (New Wage Code 2025 mandates ≥50%)
  HRA = Basic × 50% (metro) or 40% (non-metro)
  Employer EPF = Basic × 12%
  Gratuity Provision = Basic × 15/26 ≈ 4.81% of Basic/yr (paid on exit after 5yr)
  Special Allowance = CTC − Basic − HRA − Employer EPF − Gratuity (balancing figure)

STEP 2 — EPF SPLIT (Employer's 12%):
  → EPF account: Basic × 3.67% (goes to employee's PF account)
  → EPS (pension): min(Basic, ₹15,000/mo) × 8.33%
    EPS cap: ₹15,000 × 8.33% = ₹1,250/mo = ₹15,000/yr max
    If Basic > ₹15,000/mo: the excess 8.33% also goes to EPF account
  Employee EPF = Basic × 12% (deducted from salary, goes to PF account)
  Total PF accrual/yr = Employee EPF + Employer EPF = Basic × 24%

STEP 3 — COMPUTE GROSS SALARY:
  Gross = CTC − Employer EPF − Gratuity Provision

STEP 4 — DEDUCTIONS:
  EPF (Employee): Basic × 12% (mandatory)
  Professional Tax: ₹2,400/yr (₹200/mo) in most states
  Income Tax (TDS): Per applicable slab (see tax regime)

STEP 5 — TAKE-HOME:
  Annual Take-Home = Gross − EPF(employee) − PT − Income Tax
  Monthly In-Hand = Annual Take-Home ÷ 12

QUICK REFERENCE:
  In-hand ≈ 60-72% of CTC (varies by tax bracket)
  Higher Basic → more EPF/Gratuity → better retirement, lower in-hand
  EPF earns 8.15%/yr, EEE (tax-free at all stages)
  Gratuity: tax-free up to ₹20L, only after 5yr continuous service

EXAMPLE (₹24 LPA CTC, 50% Basic):
  Basic: ₹12L | HRA: ₹6L | Employer EPF: ₹1.44L | Gratuity: ₹57,692
  Gross: ₹21,98,308 | EPF(Emp): ₹1.44L | PT: ₹2,400
  Tax(New): ~₹3.49L | Take-home: ~₹17.03L/yr ≈ ₹1.42L/mo
"""

# ──────── SALARY STRUCTURE ────────
SECTIONS["salary_structure"] = """
INDIAN SALARY STRUCTURE:

CTC (Cost to Company) = Gross Salary + Employer EPF + Gratuity Provision + Benefits
Gross = Basic + HRA + DA + Special Allowance + Bonus + Other Allowances

COMPONENTS:
  Basic Pay: 40-50% of CTC (New Wage Code 2025 mandates ≥50%)
  HRA: 40-50% of Basic (50% in metro) — exemption in Old Regime only
  Special Allowance: Balancing figure (fully taxable)
  Statutory Bonus: ₹7,000/yr or 8.33% of (Basic+DA)

DEDUCTIONS FROM GROSS:
  EPF (Employee): 12% of Basic | PT: ₹2,400/yr | TDS: per tax slab
  ESI: Only if gross ≤₹21,000/mo (0.75% + 3.25%)

TAKE-HOME = Gross − EPF(employee) − PT − TDS
Higher Basic → more EPF/Gratuity (good retirement) but lower in-hand
"""

# ──────── EPF RULES ────────
SECTIONS["epf_rules"] = """
EMPLOYEE PROVIDENT FUND (EPF):

CONTRIBUTIONS:
  Employee: 12% of (Basic + DA), mandatory, deducted from salary
  Employer: 12% of (Basic + DA), split into:
    → 3.67% to EPF account  |  8.33% to EPS (capped at ₹15,000/mo Basic)
    Max EPS: ₹15,000 × 8.33% = ₹1,250/mo = ₹15,000/yr
    If Basic > ₹15,000/mo: excess 8.33% redirected to EPF

INTEREST: 8.15% p.a., compounded annually
TAX: EEE (exempt at contribution, growth, withdrawal)
  Exception: Employee contribution > ₹2.5L/yr → interest on excess taxable

WITHDRAWAL: Full at 58 or 2mo after leaving job
  Partial: Home (7yr service), medical, education, marriage
  75% after 1mo unemployed, 100% after 2mo

VPF: Extra voluntary contribution above 12%, same 8.15% interest, EEE

CTC IMPACT (@₹30L CTC, 50% Basic = ₹15L):
  EPF Employee = ₹1.8L/yr | EPF Employer = ₹1.8L/yr
  Total annual accrual: ₹3.6L growing at 8.15% — significant retirement corpus
"""

# ──────── GRATUITY ────────
SECTIONS["gratuity"] = """
GRATUITY RULES:

ELIGIBILITY: 5 continuous years of service (relaxed for death/disability)

FORMULA: Gratuity = Last Basic × 15/26 × Years of Service
  (15 days' salary per year, 26 working days/month)

TAX: Exempt up to ₹20,00,000 (Twenty Lakhs)

CTC IMPACT: Employer provisions ~4.81% of Basic annually
  NOT paid monthly — paid only on exit after 5+ years
  Reduces in-hand but builds a guaranteed exit benefit

EXAMPLE (Basic ₹60,000/mo, 8 years):
  Gratuity = ₹60,000 × 15/26 × 8 = ₹2,76,923 (fully tax-free)
  Annual provision in CTC = ₹60,000 × 12 × 15/26 ÷ 12 = ₹34,615/yr

NOTE: Factor gratuity into job-change decisions (forfeit if <5yr service)
"""

# ──────── TAX NEW REGIME ────────
SECTIONS["tax_new_regime"] = """
INCOME TAX — NEW REGIME (FY 2025-26, Default):

Standard Deduction: ₹75,000

Tax Slabs (on income after standard deduction):
  ₹0 – ₹4,00,000           → NIL
  ₹4,00,001 – ₹8,00,000    → 5%
  ₹8,00,001 – ₹12,00,000   → 10%
  ₹12,00,001 – ₹16,00,000  → 15%
  ₹16,00,001 – ₹20,00,000  → 20%
  ₹20,00,001 – ₹24,00,000  → 25%
  Above ₹24,00,000          → 30%

REBATE u/s 87A: If total income ≤ ₹12,00,000 → TAX = ZERO
  With ₹75K standard deduction → income up to ₹12,75,000 = zero tax

Surcharge: 10% (₹50L–1Cr) | 15% (₹1–2Cr) | 25% (₹2–5Cr)
Health & Education Cess: 4% on (Tax + Surcharge)

DEDUCTIONS ALLOWED (very limited):
  ₹75,000 Standard Deduction (salaried/pensioner)
  80CCD(2): Employer NPS contribution (up to 14% of salary)
  80CCH: Agniveer Corpus Fund
  NO 80C, 80D, HRA exemption, 24(b), LTA in new regime

WHEN TO CHOOSE: Best for people with few deductions (<₹3-4L in 80C/80D/HRA etc.)
"""

# ──────── TAX OLD REGIME ────────
SECTIONS["tax_old_regime"] = """
INCOME TAX — OLD REGIME (FY 2025-26, Optional):

Standard Deduction: ₹50,000

Tax Slabs:
  ₹0 – ₹2,50,000          → NIL
  ₹2,50,001 – ₹5,00,000   → 5% (Rebate u/s 87A if income ≤ ₹5L)
  ₹5,00,001 – ₹10,00,000  → 20%
  Above ₹10,00,000         → 30%

DEDUCTIONS AVAILABLE:
  80C (₹1.5L max): EPF + PPF + ELSS + LIC + NSC + SCSS + Tax FD + Tuition + Home loan principal + SSY
  80CCD(1B): Additional ₹50K for NPS
  80D: Health insurance — ₹25K self + ₹25K parents (₹50K if senior)
  80E: Education loan interest — no limit, up to 8 years
  24(b): Home loan interest — ₹2L (self-occupied), unlimited (let-out)
  80TTA: Savings interest up to ₹10K
  80G: Charitable donations (50-100%)
  HRA Exemption: Min(Actual HRA, 50/40% of Basic, Rent − 10% of Basic)
  LTA: Actual travel cost for 2 journeys in 4-year block

WHEN TO CHOOSE: Best if total deductions > ₹3.75L (80C + 80D + HRA + 24b + NPS)
  At ₹15L income: New tax ~₹1.17L vs Old (₹4L deductions) ~₹1.04L → Old saves ₹13K
  At ₹25L income: New tax ~₹3.64L vs Old (₹5L deductions) ~₹3.28L → Old saves ₹36K
"""

# ──────── TAX DEDUCTIONS DETAIL ────────
SECTIONS["tax_deductions_detail"] = """
TAX DEDUCTIONS — DETAILED BREAKDOWN (Old Regime):

SECTION 80C (₹1,50,000 limit — most used):
  EPF contribution (auto-deducted): typically ₹50K–₹1.8L/yr already fills part of 80C
  PPF: ₹500–₹1.5L/yr, 15yr maturity, 7.1% interest, EEE
  ELSS Mutual Funds: 3yr lock-in, equity returns ~12-15%, best tax-saving investment
  Life Insurance premium (term plan premium counts)
  Children tuition fees (max 2 children, full-time education)
  Home loan principal repayment
  SSY (Sukanya Samriddhi): ₹250–₹1.5L/yr, girl child <10, 8.2%, EEE
  NSC: 5yr, 7.7% | Tax-saver FD: 5yr, ~7% | SCSS: 8.2% (seniors)

NOTE: EPF auto-deduction often uses ₹50K–₹1L of 80C limit.
Plan remaining investments: ELSS (equity) > PPF (debt) > NSC/FD

80CCD(1B): ₹50,000 EXTRA for NPS (above 80C) → total 80C+NPS = ₹2L effective

80D HEALTH INSURANCE:
  Self/family: ₹25,000 (₹50,000 if senior citizen)
  Parents: ₹25,000 additional (₹50,000 if parents are senior)
  Preventive health check-up: ₹5,000 (within 80D limit)
  Max 80D deduction: ₹1,00,000 (self senior + parents senior)

HRA EXEMPTION (salaried, paying rent):
  Exempt = Min of:
    (a) Actual HRA received from employer
    (b) 50% of Basic (metro city) or 40% of Basic (non-metro)
    (c) Rent paid − 10% of Basic
  Must have rent receipts. No HRA if living in own house.
"""

# ──────── FINANCIAL FORMULAS ────────
SECTIONS["financial_formulas"] = """
FINANCIAL FORMULAS:

SIP (Systematic Investment Plan):
  Future Value = P × [((1+r)^n − 1) / r] × (1+r)
  P = monthly investment, r = monthly rate (annual% ÷ 1200), n = total months
  Example: ₹10,000/mo @12% for 20yr → n=240, r=0.01
  FV = 10,000 × [((1.01)^240 − 1) / 0.01] × 1.01 ≈ ₹99.9L

EMI (Equated Monthly Installment):
  EMI = P × r × (1+r)^n  /  ((1+r)^n − 1)
  P = loan principal, r = monthly rate (annual% ÷ 1200), n = tenure months
  Example: ₹50L @8.5% for 20yr → EMI ≈ ₹43,391/mo

Compound Interest: A = P × (1 + r/n)^(n×t)
  P=principal, r=annual rate (÷100), n=compounding frequency, t=years

CAGR: ((Ending Value / Beginning Value)^(1/years) − 1) × 100

Rule of 72: Years to double ≈ 72 ÷ Annual Return%
  @12% → doubles in 6 years | @8% → 9 years | @15% → 4.8 years

Retirement Corpus:
  1. Future monthly expense = Current × (1+inflation)^years_to_retire
  2. Annual need = Future monthly × 12
  3. Real rate = (1+return)/(1+inflation) − 1
  4. Corpus = Annual need × [(1 − (1+real_rate)^(-retirement_years)) / real_rate]
  5. SIP needed = Corpus × monthly_rate / ((1+monthly_rate)^months − 1)

Real Return = ((1+nominal)/(1+inflation) − 1) × 100
  Equity 12% − Inflation 6% → Real ~5.66%
"""

# ──────── INVESTMENT VEHICLES ────────
SECTIONS["investment_vehicles"] = """
INDIAN INVESTMENT OPTIONS (FY 2025-26):

TAX-FREE / EEE:
  PPF: 7.1%, 15yr lock, ₹1.5L/yr max — best safe debt option
  EPF: 8.15%, employer-matched — forced retirement savings
  SSY: 8.2%, girl child, ₹1.5L/yr max — highest safe return

TAX-SAVING (80C):
  ELSS MF: 3yr lock, ~12-15% long-term, best equity tax-saver
  NPS: 80CCD(1B) ₹50K extra deduction, ~10-12% equity option, partial lock till 60

MARKET-LINKED:
  Equity MF: Large cap 10-12%, Mid 12-15%, Small 15-18% (long-term averages)
  Index Funds: Nifty 50 ~12% CAGR (20yr), lowest expense ratio 0.1-0.2%
  SGB: 2.5% interest + gold price, 8yr, LTCG tax-free at maturity

FIXED INCOME:
  FD: 7-7.5% (top banks), fully taxable at slab rate
  RBI Bonds: 7.75%, 7yr, non-transferable
  SCSS: 8.2%, 5yr, ₹30L max, seniors only, quarterly payout
  POMIS: 7.4%, 5yr, ₹9L/₹15L max, monthly income

MUTUAL FUND TAXATION (FY 2025-26):
  Equity (>65% equity): LTCG 12.5% above ₹1.25L (>1yr), STCG 20% (<1yr)
  Debt MF: Taxed at income slab rate (no indexation post Apr 2023)
  Equity LTCG harvesting: Sell and rebuy ₹1.25L gains yearly to use tax-free limit
"""

# ──────── INSURANCE GUIDELINES ────────
SECTIONS["insurance_guidelines"] = """
INSURANCE PLANNING (India):

TERM LIFE INSURANCE:
  Cover needed: 10-15× annual income (sole earner), 8-10× (dual income)
    + Outstanding loans + Children's future education/wedding costs
  Buy online (40-60% cheaper) at age 25-30 for lowest premiums
  Premium: ~₹500-800 per ₹1Cr cover per year (30yr non-smoker, online)
  Top plans: HDFC Click2Protect, ICICI iProtect, Max Life, LIC Tech Term
  Claim settlement ratio: LIC 98.6%, HDFC Life 99.1%, Max Life 99.5%

HEALTH INSURANCE:
  Base: Family floater ₹10-25L (₹12K-30K/yr premium)
  Super top-up: ₹50L-1Cr (₹3-5K/yr) — extremely cost-effective
  Parents (60+): Separate policy ₹10-25L (₹20-40K/yr)
  Top insurers: Star Health, HDFC Ergo, ICICI Lombard, Care Health, Niva Bupa

80D TAX BENEFIT:
  Self/family: ₹25K deduction (₹50K if senior)
  Parents: ₹25K additional (₹50K if senior)
  Max total: ₹1,00,000 | Tax saved at 30% bracket: up to ₹30,000/yr

AVOID: ULIPs, endowment, money-back plans, return-of-premium
RULE: "Buy Term Insurance, Invest the Difference" in ELSS/index funds
"""

# ──────── LOAN RULES ────────
SECTIONS["loan_rules"] = """
LOAN RULES (India):

HOME LOAN:
  Rates: 8.25-9.5% floating (linked to repo rate)
  LTV: 90% (≤₹30L), 80% (₹30-75L), 75% (>₹75L)
  Max tenure: 30 years | No prepayment penalty (floating rate, RBI mandate)
  Tax: 24(b) interest ₹2L + 80C principal ₹1.5L (old regime)
  Joint loan: Both co-borrowers claim deductions independently
  PMAY: Interest subsidy for EWS/LIG/MIG (₹2.67L max benefit)

AFFORDABILITY RULE:
  EMI ≤ 40% of net take-home (safe) | ≤50% (stretched, risky)
  Total obligations (all EMIs + credit card minimum) ≤ 50-60% of take-home
  Banks use FOIR (Fixed Obligation to Income Ratio) — max 50-60%

ELIGIBILITY: CIBIL 750+ for best rates. 724-749: slightly higher. Below 700: risky.

OTHER LOANS:
  Personal: 10.5-24% | 1-5yr | No collateral | No tax benefit
  Car: 8-12% | Max 7yr | No tax benefit
  Education: 8-14% | 80E deduction (interest only, no limit, up to 8yr)
  Gold: 7-12% | 75% LTV | Quick disbursement
  LAP: 8.5-12% | 60% of property value

PREPAYMENT STRATEGY:
  Highest-rate loan first (avalanche method) OR smallest-balance first (snowball)
  Home loan: Don't prepay aggressively if using 24(b) deduction in old regime
"""

# ──────── RETIREMENT PLANNING ────────
SECTIONS["retirement_planning"] = """
RETIREMENT PLANNING (India):

CORPUS CALCULATION:
  Target: 25-30× annual expenses at retirement (Safe Withdrawal Rate 3-4%)
  Account for 6% inflation and plan to age 85+
  DO NOT use CTC/income as expense — use actual monthly spending (~50-60% of take-home)

RETIREMENT TOOLKIT:
  EPF: ~8.15%, EEE, employer-matched — count as debt allocation in portfolio
  PPF: 7.1%, ₹1.5L/yr, 15yr cycles, EEE — safe long-term accumulation
  NPS: Extra ₹50K tax benefit (80CCD(1B)), equity option ~10-12%
    At 60: 60% lump-sum (tax-free), 40% annuity (taxable pension)
  Gratuity: After 5yr, tax-free up to ₹20L — count in corpus

STEP-UP SIP: Increase SIP 10% yearly with salary increments
  ₹10K/mo + 10% step-up @12% for 25yr ≈ ₹2.2Cr vs ₹1.9Cr flat SIP

FIRE (Financial Independence Retire Early):
  Lean FIRE: 25× expenses | Fat FIRE: 35× | Coast FIRE: enough to let compounding finish

BUCKET STRATEGY (post-retirement):
  Bucket 1 (0-3yr): Liquid/FD — immediate living expenses
  Bucket 2 (3-10yr): Debt MF, balanced/hybrid — medium-term
  Bucket 3 (10yr+): Equity — long-term growth beating inflation

POST-RETIREMENT INCOME:
  SCSS: 8.2%, ₹30L, quarterly interest | PMVVY: 7.4%, ₹15L, monthly
  SWP from MF: Most flexible, withdraw 3-4% annually
  Senior FD: Extra 0.5% interest at most banks
"""

# ──────── BUDGET PLANNING ────────
SECTIONS["budget_planning"] = """
BUDGET PLANNING (India):

IMPORTANT: Always budget from TAKE-HOME pay, never CTC. Choose the framework that
best fits the user's life stage, city, family size, EMI load, and goals.

FRAMEWORK 1 — 50/30/20 (Standard):
  50% Needs: Rent, groceries, utilities, transport, insurance, min EMI
  30% Wants: Dining, shopping, travel, subscriptions, entertainment
  20% Savings: Emergency → Insurance → SIPs/PPF → Goals
  BEST FOR: Single earners, no major debt, stable income

FRAMEWORK 2 — 60/20/20 (High-Cost City):
  60% Needs (metro rents are 30-40% of take-home alone)
  20% Wants | 20% Savings
  BEST FOR: Mumbai, Bangalore, Delhi residents with high rent

FRAMEWORK 3 — 40/20/40 (Aggressive Saver / FIRE):
  40% Needs | 20% Wants | 40% Savings+Investing
  BEST FOR: Dual income, no kids, early retirement goal, high earners

FRAMEWORK 4 — 70/10/20 (EMI Heavy):
  70% Needs+EMIs (when EMI alone is 30-40% of take-home)
  10% Wants | 20% Savings (non-negotiable minimum)
  BEST FOR: Active home/car loan, or single income supporting family

FRAMEWORK 5 — Pay Yourself First:
  Save 20-30% FIRST (auto-SIP on salary day), then spend the rest freely
  No granular budgeting. BEST FOR: Discipline-challenged, high earners

HOW TO CHOOSE:
  - Total EMIs > 30% of take-home → Framework 4 (EMI Heavy)
  - Metro city rent > 25% of take-home → Framework 2 (High-Cost City)
  - FIRE/aggressive saving goal → Framework 3
  - First-time budgeter, typical situation → Framework 1 (50/30/20)
  - Hates tracking expenses → Framework 5

SAVINGS PRIORITY (regardless of framework):
  1. Emergency Fund: 6 months of essential expenses in liquid fund
  2. Term Life + Health Insurance: non-negotiable before investing
  3. EPF/PPF: retirement foundation (EPF already auto-deducted)
  4. ELSS/Index SIP: tax saving + wealth building
  5. Goal-based SIPs: children education, house down payment, etc.

INDIAN COST BENCHMARKS (Metro, 2025):
  Rent: ₹15-30K (1BHK), ₹25-50K (2BHK) depending on city
  Groceries: ₹8-15K/mo family of 3-4 | Utilities: ₹3-5K/mo
  Health insurance: ₹15-25K/yr | Term insurance: ₹10-20K/yr
"""

# ──────── CRYPTO TAX ────────
SECTIONS["crypto_tax_india"] = """
CRYPTOCURRENCY TAX & RULES (India):

TAX RATE: Flat 30% on ALL crypto gains — no slab benefit
  No deduction allowed except cost of acquisition
  No loss set-off against any other income
  No carry-forward of crypto losses

TDS: 1% on crypto transactions >₹10,000/yr (Section 194S)
  Deducted by exchange at time of sale

REPORTING: Schedule VDA in ITR — mandatory disclosure
  Crypto gifts: Taxable at 30% for receiver (if >₹50K from non-relative)

PLANNING:
  Tax harvesting NOT effective (30% flat, no set-off)
  Hold long-term to reduce transaction frequency (less TDS events)
  Keep ≤5% of portfolio in crypto, ONLY discretionary surplus
  Build core portfolio (MF, PPF, insurance) FIRST
  Use Indian exchanges: WazirX, CoinDCX, CoinSwitch, ZebPay
"""

# ──────── STOCK MARKET ────────
SECTIONS["stock_market_india"] = """
INDIAN STOCK MARKET REFERENCE:

STRUCTURE: NSE (Nifty 50) + BSE (Sensex 30) | T+1 settlement | SEBI regulated
  Trading: 9:15 AM – 3:30 PM IST | Pre-open: 9:00-9:15 AM

KEY INDICES:
  Nifty 50: 50 large caps, avg P/E 20-22×
  Sensex: 30 blue chips (BSE)
  Bank Nifty: 12 banking stocks | Nifty Midcap 150, Smallcap 250

TAXATION (FY 2025-26):
  Equity LTCG (>1yr): 12.5% above ₹1.25L exemption per year
  Equity STCG (<1yr): 20%
  Dividend: Taxed at slab rate (no DDT since 2020)
  STT: 0.1% on sell (equity delivery)

VALUATION METRICS:
  P/E ratio: <15 value, 15-25 fair, >25 expensive (sector matters)
  P/B: <1 deep value, 1-3 fair | ROE: >15% good | D/E: <1 safe
  Dividend Yield: >2% good for income stocks

SMART PRACTICES:
  SIP in index fund for passive investors (Nifty 50, Nifty Next 50)
  Sector diversification: avoid >25% in one sector
  Tax harvesting: Sell and rebuy ₹1.25L LTCG yearly
"""


# ──────── CAPITAL GAINS TAX REFERENCE ────────
SECTIONS["capital_gains_tax"] = """
CAPITAL GAINS TAX — INDIA FY 2025-26:

EQUITY & EQUITY MUTUAL FUNDS:
  LTCG (>1yr): 12.5% above ₹1.25L exemption + 4% cess
  STCG (<1yr): 20% + 4% cess
  No indexation benefit for equity
  TAX HARVESTING: Sell ₹1.25L gains yearly, rebuy immediately → reset cost basis

DEBT MUTUAL FUNDS (purchased after Apr 2023):
  All gains taxed at SLAB RATE regardless of holding period
  No LTCG benefit. Treat like FD interest for tax purposes.

GOLD & PROPERTY (post July 2024):
  LTCG (>24 months): 12.5% + 4% cess (NO indexation)
  STCG (<24 months): At slab rate
  Property: Sec 54 exemption if reinvest in another house within 2yr

CRYPTOCURRENCY (VDA):
  Flat 30% + 4% cess on ALL profits — no slab benefit
  1% TDS on transfers > ₹10K/yr
  NO loss set-off (not even against crypto gains from other coins)
  NO deduction except acquisition cost
"""


# ──────── FINANCIAL PLANNING WORKED EXAMPLES ────────
SECTIONS["worked_examples"] = """
WORKED EXAMPLES — How to think through financial queries:

EXAMPLE 1: "I earn ₹25 LPA CTC. Should I prepay my ₹40L home loan?"
THINKING: CTC ₹25L → Take-home ~₹1.53L/mo. Home loan @8.5% → EMI ~₹34K.
  EMI/Take-home = 22% (well within 40% safe). Home loan effective rate after
  tax benefit = ~5.9% (30% bracket). Equity SIP returns ~12%.
  VERDICT: Invest surplus in SIP (12% > 5.9%). Prepay only if you want peace of mind.

EXAMPLE 2: "I'm 28, ₹15 LPA. Plan my financial life."
PRIORITY ORDER:
  1. Emergency fund: 6mo expenses = ₹3.3L (park in liquid fund)
  2. Health insurance: ₹10L floater = ~₹8K/yr
  3. Term life: ₹1Cr cover = ~₹10K/yr
  4. SIP: ₹15K/mo (20% take-home) in Nifty 50 + Flexi Cap
  5. NPS: ₹50K/yr for extra 80CCD(1B) deduction
  6. Build PPF for debt allocation: ₹1.5L/yr max

EXAMPLE 3: "Old vs New regime for ₹18 LPA?"
  New: Gross ~₹16.4L − ₹75K std ded = ₹15.65L taxable → Tax ≈ ₹1.82L
  Old: Gross ₹16.4L − ₹50K std ded. If using: 80C ₹1.5L + 80D ₹25K + HRA ₹2.4L
    → Taxable ≈ ₹12.15L → Tax ≈ ₹1.45L. Old regime saves ₹37K.
  BUT: Old regime needs ₹4.15L in deductions to beat New → only worth it with
  home loan interest (24b) or significant rent (HRA).
"""


# ──────── LOAN STRATEGIES ────────
SECTIONS["loan_strategies"] = """
LOAN STRATEGIES — EXPERT DECISION FRAMEWORK:

PREPAY vs INVEST DECISION TREE:
  If loan rate > 10%: PREPAY (guaranteed high return)
  If loan rate 8-10%: PREPAY if risk-averse, INVEST if long horizon (>10yr)
  If loan rate < 8%: INVEST (equity SIP @12% beats loan cost by wide margin)
  NOTE: Home loan has tax benefit — effective rate is lower

EFFECTIVE COST AFTER TAX (30% bracket):
  Home loan 8.5% → effective 5.95% (24b benefit)
  Education loan 9% → effective 6.3% (80E benefit)
  Personal loan 12% → effective 12% (no tax benefit)
  Car loan 9% → effective 9% (no tax benefit!)

PREPAYMENT IMPACT (₹50L home loan, 8.5%, 20yr):
  ₹5L prepayment in Year 2: Saves ₹9.8L interest + 4.2yr tenure
  ₹5L prepayment in Year 10: Saves ₹4.1L interest + 2.8yr tenure
  KEY INSIGHT: Early prepayments have exponentially more impact

RENT vs BUY FRAMEWORK:
  Buy if: Property appreciation > loan rate, plan to stay 10yr+, rental yield >3%
  Rent if: Rent < EMI, invest difference in SIP @12%, plan to relocate in <7yr
  Rule of thumb: If price/annual-rent > 25, renting is better
"""


# ──────── GOVERNMENT SAVINGS SCHEMES ────────
SECTIONS["govt_schemes"] = """
INDIAN GOVERNMENT SAVINGS & PENSION SCHEMES (FY 2025-26):

═══ SMALL SAVINGS SCHEMES (Rates revised quarterly by MoF) ═══

PPF (Public Provident Fund):
  Rate: 7.1% (compounded annually) | Lock-in: 15 years (extendable in 5yr blocks)
  Limit: ₹500/yr min, ₹1,50,000/yr max | Tax: EEE (deposit+interest+maturity all exempt)
  Partial withdrawal: From 7th year (50% of 5th year balance) | Loan: Yr 3-6 against balance
  80C: Full ₹1.5L eligible | Best for: Conservative investors, retirement corpus, children

SSY (Sukanya Samriddhi Yojana):
  Rate: 8.2% (highest among small savings) | Lock-in: 21 years from opening
  Eligibility: Girl child aged 0-10 | Max 2 accounts (one per girl child)
  Deposit: ₹250/yr min, ₹1,50,000/yr max, deposit mandatory for 14 years
  Partial withdrawal: 50% after girl turns 18 (for education only)
  Premature closure: Marriage after 18, or account holder death
  Tax: EEE (Section 80C + interest exempt + maturity exempt)
  Best for: Parents of girl children — highest guaranteed return + full tax exemption

NPS (National Pension System):
  Returns: 9-12% (market-linked, based on asset allocation)
  Eligibility: 18-70 years | Retirement: Payout at 60
  Tier-I (pension): ₹500/yr min, no max. Lock till 60 (partial withdrawal after 3yr for specific needs)
  Tier-II (investment): ₹250 min, fully liquid (no tax benefit except govt employees)
  At 60: Minimum 40% must buy annuity, up to 60% lump sum tax-free (if ≤60% of corpus)
  Tax benefits: 80CCD(1) within 80C ₹1.5L + 80CCD(1B) additional ₹50K
  Employer NPS: 80CCD(2) up to 14% of basic (no cap!) — huge benefit for corporate NPS
  Asset allocation: E (equity max 75%), C (corporate bonds), G (govt bonds), A (alternatives)
  Auto choice: Life Cycle Fund — equity reduces as age increases
  Best for: Additional tax saving beyond 80C, long-term retirement corpus

NSC (National Savings Certificate):
  Rate: 7.7% (compounded annually, paid at maturity) | Tenure: 5 years fixed
  Investment: ₹1,000 min, no max | Available at: Post office
  Tax: 80C eligible (up to ₹1.5L). Interest taxable but reinvested interest qualifies for 80C
  No premature withdrawal (except death/court order)
  Best for: Risk-averse tax savers, guaranteed returns, 80C filling

KVP (Kisan Vikas Patra):
  Rate: 7.5% (compounded annually) | Doubles in: ~115 months (~9.6 years)
  Investment: ₹1,000 min, no max | Available at: Post office, selected banks
  Lock-in: 2.5 years (premature encashment after) | No 80C benefit
  Best for: Conservative investors wanting guaranteed doubling, no tax benefit

SCSS (Senior Citizens Savings Scheme):
  Rate: 8.2% (simple interest, paid quarterly) | Tenure: 5 years (extendable by 3)
  Investment: ₹1,000 min, ₹30,00,000 max | Eligibility: 60+ (or 55+ for VRS/superannuation)
  Tax: 80C eligible. Quarterly interest is taxable (TDS if interest > ₹50K/yr)
  Premature closure: 1% penalty (1-2yr), 0.5% (2-5yr)
  Best for: Retirees seeking regular income — highest rate among senior schemes

POMIS (Post Office Monthly Income Scheme):
  Rate: 7.4% (simple interest, paid monthly) | Tenure: 5 years
  Investment: ₹1,000 min, ₹9,00,000 max (single), ₹15,00,000 (joint)
  Tax: No 80C. Interest fully taxable at slab rate
  Premature: After 1yr (1-3yr: 2% penalty, 3-5yr: 1%)
  Best for: Monthly income for retirees/homemakers — predictable cash flow

APY (Atal Pension Yojana):
  Pension: ₹1,000 to ₹5,000/month (fixed) | Starts at: Age 60
  Eligibility: 18-40 years, must have bank account + Aadhaar
  Contribution: ₹42-1,454/month depending on entry age and pension chosen
  Tax: 80CCD(1) within 80C ₹1.5L | Govt co-contribution discontinued (was till 2020)
  After death: Spouse gets same pension → after spouse, nominee gets corpus
  Best for: Unorganised sector workers, guaranteed minimum pension

EPF (Employee Provident Fund):
  Rate: 8.25% (FY 2024-25) | Employee: 12% of Basic+DA | Employer: 12% (3.67% EPF + 8.33% EPS)
  EPS cap: ₹15,000/month basic | Voluntary PF: Employee can contribute more via VPF (same rate)
  Withdrawal: Full after 2 months unemployment, or retirement at 58
  Partial: Housing (7yr), Medical, Education, Marriage (specific conditions)
  Tax: EEE up to ₹2.5L/yr contribution. Above ₹2.5L: interest taxable

═══ COMPARISON TABLE ═══
  Highest rate: SSY 8.2%, EPF 8.25%, SCSS 8.2%
  Full tax-free (EEE): PPF, SSY, EPF (up to ₹2.5L)
  Monthly income: POMIS, SCSS (quarterly)
  Extra 80C benefit: PPF, SSY, NSC, ELSS, NPS (+ extra ₹50K 80CCD1B)
  No lock-in: NPS Tier-II, POMIS (after 1yr)
  Best for girl child: SSY (8.2%, 21yr)
  Best for pension: NPS (market-linked) + APY (guaranteed)
"""


# ──────── BANKING ACCOUNT TYPES ────────
SECTIONS["banking_accounts"] = """
INDIAN BANKING ACCOUNT TYPES — COMPLETE GUIDE:

═══ RESIDENT ACCOUNTS ═══

SAVINGS ACCOUNT:
  Purpose: Daily banking, salary credit, UPI/NEFT/RTGS
  Interest: 2.5-7% (small finance banks offer higher: AU, Equitas)
  Min balance: ₹0 (Jan Dhan, basic) to ₹10,000 (premium)
  Tax: Interest exempt up to ₹10,000/yr (Section 80TTA), ₹50,000 for seniors (80TTB)
  DICGC insurance: ₹5,00,000 per depositor per bank (covers savings + FD combined)

CURRENT ACCOUNT:
  Purpose: Business transactions, no transaction limits
  Interest: NIL | Min balance: ₹10,000-₹1,00,000 (varies by bank)
  Features: Cheque book, overdraft facility, high transaction limits
  Tax: No interest, no TDS
  Best for: Businesses, traders, professionals with high transaction volume

SALARY ACCOUNT:
  Purpose: Employer-linked, zero balance | Converts to savings if no salary credit for 3 months
  Benefits: Zero balance, free debit card, higher ATM limits, pre-approved loans
  Best for: Salaried employees (auto-opened by employer)

FIXED DEPOSIT (FD):
  Rate: 6.5-7.5% (regular), +0.25-0.5% for seniors | Tenure: 7 days to 10 years
  Tax: TDS 10% if interest > ₹40K/yr (₹50K for seniors). Submit Form 15G/15H to avoid TDS if total income < taxable limit
  Tax-saver FD: 5yr lock-in, 80C eligible up to ₹1.5L (only at selected banks)
  Premature withdrawal: 0.5-1% penalty on applicable rate
  Sweep-in FD: Auto-breaks FD if savings balance insufficient — best of both worlds

RECURRING DEPOSIT (RD):
  Rate: Similar to FD rates | Monthly deposit: ₹100 onwards
  Compounding: Quarterly (per RBI norms)
  Tax: Interest taxable at slab rate. TDS applicable per RBI norms
  Best for: Building discipline for regular savings, fixed monthly investment

═══ NRI ACCOUNTS (Non-Resident Indians) ═══

NRE ACCOUNT (Non-Resident External):
  Purpose: Park foreign earnings in India (in INR)
  Deposits: Only foreign remittances (salary/income earned abroad)
  Withdrawal: Freely repatriable (can send money back abroad anytime)
  Interest: Tax-FREE in India (both savings and FD) — biggest advantage
  Types: NRE Savings, NRE FD (rates similar to regular FD, sometimes slightly lower)
  Joint: Only with another NRI/PIO (not with resident Indian)
  On return to India: Must convert to regular savings account within reasonable time
  Best for: NRIs who want to send money home, earn tax-free interest, and maintain full repatriability

NRO ACCOUNT (Non-Resident Ordinary):
  Purpose: Manage income earned IN India (rent, pension, dividends, interest)
  Deposits: Both Indian and foreign income allowed
  Withdrawal: Repatriable up to $1 million/year (after tax clearance and CA certificate)
  Interest: TAXABLE in India at 30% + cess (TDS deducted by bank)
  Tax treaty: Can claim DTAA benefit to reduce TDS (submit Form 10F + TRC)
  Joint: Can hold with resident Indian
  On return: Becomes regular savings account
  Best for: NRIs with Indian rental income, pension, or Indian investments

FCNR ACCOUNT (Foreign Currency Non-Resident):
  Purpose: Keep money in foreign currency (USD/GBP/EUR/JPY/CAD/AUD)
  Type: Only term deposits (no savings — minimum 1yr, max 5yr)
  Key advantage: NO currency conversion risk — deposit and maturity in foreign currency
  Interest: Tax-FREE in India | Rates: Based on LIBOR/SOFR (typically 3-5%)
  Repatriation: Fully repatriable (principal + interest)
  Best for: NRIs who plan to return and don't want INR risk, or parking surplus foreign currency

NRE vs NRO vs FCNR — WHEN TO USE:
  Foreign salary → India: NRE (tax-free, fully repatriable)
  Indian rental/dividend income: NRO (mandatory — Indian income must go here)
  Parking USD/GBP without INR risk: FCNR (term deposit in foreign currency)
  Planning to return soon: NRE (convert to savings) + FCNR (avoid forex loss)
  Want joint account with resident: Only NRO allows this

IMPORTANT NRI RULES:
  • NRIs CANNOT hold regular savings/current accounts — must convert on leaving India
  • NRIs can invest in MF, stocks (through PIS route), real estate (except agricultural land)
  • NRI FD rates may differ from resident rates
  • TDS on NRO: 30% on interest + surcharge + cess (effective ~31.2%)
  • DTAA: Double Tax Avoidance Agreement — claim credit in country of residence
  • FEMA rules: All NRI accounts governed by RBI/FEMA — non-compliance is serious

═══ OTHER SPECIAL ACCOUNTS ═══

JAN DHAN ACCOUNT (PMJDY):
  Purpose: Financial inclusion — zero balance basic savings
  Benefits: Free accident insurance ₹2L, life cover ₹30K, overdraft ₹10K, RuPay card
  Eligibility: Any Indian resident without bank account
  Best for: Low-income individuals, rural population, govt benefit (DBT) recipients

DEMAT ACCOUNT:
  Purpose: Hold shares, bonds, ETFs, govt securities in electronic form
  Providers: NSDL/CDSL through DPs (brokers like Zerodha, Groww, Angel One)
  Charges: AMC ₹0-300/yr + transaction charges
  Required for: Stock trading, IPO application, corporate bond investment

TRADING ACCOUNT:
  Purpose: Buy/sell securities on stock exchanges (NSE/BSE)
  Linked to: Bank account (funds) + Demat account (holdings)
  Providers: Zerodha, Groww, Angel One, Upstox (discount), ICICI Direct, HDFC Sec (full-service)
  Charges: ₹0-20 per trade (discount brokers), 0.3-0.5% (full-service)

PPF ACCOUNT (Public Provident Fund):
  Held at: Banks (SBI, ICICI, etc.) or post office
  One account per person (no joint PPF)
  Minor child: Parent can open PPF, combined limit ₹1.5L
  NRI: Cannot open new PPF. Existing PPF at time of becoming NRI continues till maturity (at 7.1%)

SUKANYA SAMRIDDHI ACCOUNT:
  Held at: Banks or post office | One per girl child, max 2 per family
  NRI: Girl child must be resident Indian
  Transfer: Can transfer between banks/post offices
"""


# ──────── GOVERNMENT WELFARE & FINANCIAL POLICIES ────────
SECTIONS["govt_policies"] = """
KEY INDIAN GOVERNMENT FINANCIAL POLICIES & PROGRAMS:

═══ DIRECT BENEFIT TRANSFER (DBT) ═══
  All subsidies (LPG, fertilizer, food, MGNREGA wages) credited directly to Jan Dhan/bank account
  Eliminates middlemen. Linked to Aadhaar + bank account

═══ TAX POLICIES (FY 2025-26) ═══
  New regime is DEFAULT (no opt-in needed). Old regime requires Form 10-IE
  Standard deduction: ₹75,000 (new), ₹50,000 (old)
  87A rebate: Income ≤ ₹12,00,000 → ZERO tax under new regime (effective ₹12,75,000 with std deduction)
  No LTCG tax up to ₹1,25,000/yr on equity (new limit from Budget 2024)
  NPS employer: 14% of basic — no cap on deduction under 80CCD(2)

═══ DIGITAL INDIA FINANCIAL INFRA ═══
  UPI: Zero MDR on transactions < ₹2,000. UPI Lite for offline payments up to ₹500
  Aadhaar-linked: Bank account, PAN, MF KYC, insurance — all linked
  DigiLocker: Store financial documents (PAN, Aadhaar, insurance policies)
  Account Aggregator: Consent-based financial data sharing between banks/NBFCs/MFs
  ONDC: Open Network for Digital Commerce — decentralized e-commerce

═══ MUDRA LOAN (PMMY) ═══
  For: Micro/small business loans without collateral
  Shishu: Up to ₹50,000 | Kishore: ₹50K-₹5L | Tarun: ₹5L-₹10L
  Interest: 7-12% depending on bank | No processing fee
  Available at: All banks, NBFCs, MFIs

═══ PM AWAS YOJANA (Housing) ═══
  CLSS: Credit Linked Subsidy of 3-6.5% on home loan interest
  EWS/LIG: Up to ₹6.5L subsidy on ₹6L loan | MIG-I: ₹4L on ₹9L | MIG-II: ₹2.35L on ₹12L
  Eligibility: No pucca house in family, income-based category

═══ STAND-UP INDIA ═══
  Loans ₹10L-₹1Cr for SC/ST/Women entrepreneurs for greenfield enterprise
  At least 1 SC/ST and 1 woman borrower per bank branch

═══ SOVEREIGN GOLD BOND (SGB) ═══
  Issued by RBI, 8yr tenure | 2.5% annual interest (semi-annual) tax-free at maturity
  LTCG: Tax-free if held till maturity | Listing: Trade on exchanges
  1 gram denomination | Max: 4kg individual, 20kg trust per fiscal year
  Best for: Long-term gold exposure with guaranteed interest

═══ PRODUCTION-LINKED INCENTIVE (PLI) ═══
  Sectors: Electronics, pharma, auto, textiles, food processing, solar, drones, etc.
  Incentive: 4-6% of incremental sales for 5 years
  Impact: Encourages domestic manufacturing, Make in India

═══ KEY REGULATORS ═══
  RBI: Banks, NBFCs, monetary policy, forex, payment systems
  SEBI: Stock exchanges, mutual funds, portfolio managers, debentures
  IRDAI: Insurance companies, health/life/general insurance
  PFRDA: NPS, APY, pension funds
  DICGC: Deposit insurance ₹5L per depositor per bank
  AMFI: Mutual fund industry body (not regulator)
"""


# ─────────────────────── Knowledge Selector ───────────────────────

# Map query keywords → relevant knowledge sections
TOPIC_KEYWORDS = {
    "ctc_to_takehome": [
        "ctc", "take home", "take-home", "in-hand", "in hand", "package",
        "lpa", "salary breakdown", "net salary", "cost to company",
        "salary calculation", "salary structure",
    ],
    "salary_structure": [
        "salary", "basic", "hra", "allowance", "payslip", "gross",
        "deduction", "special allowance", "da",
    ],
    "epf_rules": [
        "epf", "pf", "provident fund", "vpf", "eps", "pension fund",
        "employer contribution",
    ],
    "gratuity": [
        "gratuity", "5 years", "five years", "years of service",
    ],
    "tax_new_regime": [
        "new regime", "tax", "tds", "income tax", "87a", "rebate",
        "tax slab", "tax calculation",
    ],
    "tax_old_regime": [
        "old regime", "hra exemption", "section 80", "exemption",
        "regime comparison", "which regime",
    ],
    "tax_deductions_detail": [
        "80c", "80d", "80e", "80ccd", "deduction", "tax saving",
        "elss", "nps", "hra exempt", "24b", "home loan interest",
    ],
    "financial_formulas": [
        "sip", "emi", "compound interest", "formula", "calculate",
        "return", "cagr", "rule of 72", "retirement corpus",
    ],
    "investment_vehicles": [
        "invest", "ppf", "nps", "fd", "fixed deposit", "mutual fund",
        "elss", "sgb", "gold bond", "debt fund", "index fund",
        "where to invest",
    ],
    "insurance_guidelines": [
        "insurance", "term plan", "health cover", "irdai", "premium",
        "life cover", "claim", "health insurance", "term life",
    ],
    "loan_rules": [
        "loan", "home loan", "car loan", "personal loan", "mortgage",
        "prepay", "emi afford", "eligibility", "cibil",
    ],
    "retirement_planning": [
        "retire", "corpus", "pension", "fire", "senior citizen",
        "retirement", "post-retirement", "swp", "annuity",
    ],
    "budget_planning": [
        "budget", "expense", "50/30/20", "saving plan", "emergency fund",
        "financial plan", "spending", "monthly plan", "how to save",
        "allocat", "split", "manage money", "plan my", "afford",
    ],
    "crypto_tax_india": [
        "crypto", "bitcoin", "ethereum", "vda", "30% tax", "tds crypto",
    ],
    "stock_market_india": [
        "stock", "share", "nifty", "sensex", "equity", "ipo",
        "dividend", "p/e", "valuation", "stcg", "ltcg",
    ],
    "capital_gains_tax": [
        "capital gain", "ltcg", "stcg", "sell shares", "book profit",
        "profit on sale", "tax on gains", "tax harvesting", "sell shares",
    ],
    "worked_examples": [
        "example", "how to", "explain", "guide", "plan my",
        "help me", "should i", "what should",
    ],
    "loan_strategies": [
        "prepay", "prepayment", "rent vs buy", "buy vs rent",
        "loan strategy", "should i prepay", "invest or prepay",
        "loan vs invest",
    ],
    "govt_schemes": [
        "ssy", "sukanya", "girl child", "nps", "national pension",
        "nsc", "national savings", "kvp", "kisan vikas",
        "scss", "senior citizen", "pomis", "post office",
        "apy", "atal pension", "small savings", "government scheme",
        "govt scheme", "ppf", "epf", "provident fund",
        "savings scheme", "yojana", "pension scheme",
    ],
    "banking_accounts": [
        "nri", "nre", "nro", "fcnr", "bank account", "savings account",
        "current account", "salary account", "demat", "trading account",
        "jan dhan", "zero balance", "non-resident", "foreign currency",
        "repatriable", "repatriation", "dtaa", "fema",
        "sweep", "fd account", "fixed deposit account",
        "account type", "which account", "open account",
    ],
    "govt_policies": [
        "mudra", "awas yojana", "stand up india", "sgb", "sovereign gold",
        "dbt", "direct benefit", "pli", "make in india",
        "rbi", "sebi", "irdai", "pfrda", "dicgc",
        "regulator", "scheme", "government policy", "govt policy",
        "subsidy", "pmjdy", "upi", "digital india",
    ],
}

# Some queries always benefit from certain sections
ALWAYS_RELEVANT = {
    "salary_structure": ["budget", "take home", "ctc", "salary", "lpa", "package"],
    "financial_formulas": ["how much", "calculate", "plan", "need", "corpus", "sip"],
    "govt_schemes": ["which scheme", "where to invest safe", "government", "tax free"],
}

# Related topics: when a topic is selected, also consider pulling these
RELATED_TOPICS = {
    "ctc_to_takehome": ["epf_rules", "gratuity", "tax_new_regime"],
    "salary_structure": ["ctc_to_takehome", "epf_rules", "gratuity"],
    "epf_rules": ["ctc_to_takehome", "gratuity", "govt_schemes"],
    "gratuity": ["ctc_to_takehome", "epf_rules"],
    "tax_new_regime": ["tax_old_regime", "tax_deductions_detail"],
    "tax_old_regime": ["tax_deductions_detail", "tax_new_regime"],
    "retirement_planning": ["financial_formulas", "epf_rules", "govt_schemes"],
    "loan_rules": ["financial_formulas", "loan_strategies"],
    "insurance_guidelines": ["budget_planning"],
    "stock_market_india": ["capital_gains_tax"],
    "capital_gains_tax": ["stock_market_india", "tax_new_regime"],
    "loan_strategies": ["loan_rules", "financial_formulas"],
    "budget_planning": ["worked_examples"],
    "govt_schemes": ["investment_vehicles", "tax_deductions_detail"],
    "banking_accounts": ["govt_policies"],
    "govt_policies": ["govt_schemes", "banking_accounts"],
    "investment_vehicles": ["govt_schemes"],
}


def get_relevant_knowledge(query: str, max_sections: int = 3) -> str:
    """
    Select and return knowledge sections most relevant to the query.
    Uses related-topics cross-referencing to ensure the LLM gets
    complete conceptual context (e.g. salary → EPF + gratuity).
    Returns a formatted string ready for injection into LLM context.
    """
    query_lower = query.lower()
    scores: dict[str, float] = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(2 if kw in query_lower else 0 for kw in keywords)
        # Boost exact phrase matches
        for kw in keywords:
            if len(kw) > 3 and kw in query_lower:
                score += 1  # extra boost for longer keywords
        if score > 0:
            scores[topic] = score

    # Add always-relevant sections with lower priority
    for topic, triggers in ALWAYS_RELEVANT.items():
        if any(t in query_lower for t in triggers) and topic not in scores:
            scores[topic] = 1.0

    if not scores:
        # Default: give CTC pipeline and financial formulas
        scores["ctc_to_takehome"] = 1.0
        scores["financial_formulas"] = 0.5

    # Boost related topics so the LLM gets complete conceptual context
    # e.g. asking about salary should also include EPF/gratuity knowledge
    related_boosts: dict[str, float] = {}
    for topic, score in scores.items():
        if topic in RELATED_TOPICS and score >= 2:
            for related in RELATED_TOPICS[topic]:
                if related not in scores:
                    # Add related topic with half the parent's score
                    boost = score * 0.4
                    if related not in related_boosts or boost > related_boosts[related]:
                        related_boosts[related] = boost
    scores.update(related_boosts)

    # Sort by relevance score, take top N
    top_topics = sorted(scores, key=lambda k: scores[k], reverse=True)[:max_sections]

    parts = ["═══ INDIAN FINANCE REFERENCE (use for reasoning) ═══"]
    for topic in top_topics:
        parts.append(SECTIONS[topic])
    parts.append("═══ END REFERENCE ═══")

    return "\n".join(parts)


def get_section(name: str) -> str:
    """Get a specific knowledge section by name."""
    return SECTIONS.get(name, "")
