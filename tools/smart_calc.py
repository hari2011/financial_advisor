"""
Smart Calculator Dispatcher — Analyses queries and auto-runs relevant calculators.

Instead of each agent manually deciding which calculators to call,
this module understands the full financial context of a query and
runs ALL relevant calculators, cross-referencing results.

HYBRID APPROACH: Fast regex for obvious keywords → LLM reasoning fallback
for ambiguous or natural-language queries. Best of both worlds.

Think like a human financial expert:
- "Should I prepay my loan or invest?" → runs BOTH loan prepayment AND SIP,
  then compares the outcomes.
- "I earn 25 LPA, plan my retirement" → runs CTC, retirement corpus,
  SIP projections, insurance needs, emergency fund, AND step-up SIP.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("financegpt.smart_calc")

# ══════════════════════════════════════════════════════════════
# CALCULATOR TOPIC REGISTRY — Single source of truth
# Maps topic keys → human-readable descriptions for LLM classification
# ══════════════════════════════════════════════════════════════
CALC_TOPIC_REGISTRY = {
    "tax":           "Income tax calculation, 80C/80D deductions, old vs new regime, TDS, ITR — anything about tax saving or tax liability",
    "salary":        "CTC breakdown, take-home salary, in-hand pay, salary structure — anything about compensation/pay",
    "loan":          "EMI calculation, home/car/personal/education loan, borrowing, debt management — anything about loans or EMIs",
    "prepay":        "Loan prepayment, foreclosure, part-payment, closing loan early — anything about paying off debt faster",
    "invest":        "SIP, mutual funds, equity, index funds, where to invest, wealth building — anything about investing or growing money",
    "retirement":    "Retirement planning, pension, NPS, FIRE, corpus needed, post-retirement — anything about retirement",
    "insurance":     "Life insurance, health insurance, term plan, family protection — anything about insurance cover",
    "budget":        "Budget planning, expense management, emergency fund, savings discipline, 50/30/20 rule — anything about managing money",
    "hra":           "HRA exemption, rent allowance, house rent for tax — anything about HRA calculation",
    "property":      "Real estate, buying house/flat, rent vs buy, property investment — anything about property decisions",
    "gold":          "Gold investment, SGB, gold ETF, digital gold — anything about gold as investment",
    "fd":            "Fixed deposit, recurring deposit, safe/guaranteed returns — anything about bank deposits",
    "ppf":           "PPF, public provident fund — long-term tax-free savings",
    "crypto":        "Cryptocurrency, Bitcoin, Ethereum — anything about crypto investments",
    "education":     "Education planning, child education fund, study abroad, education loan — anything about education costs",
    "goal":          "Financial goal planning, saving for wedding/car/vacation/target amount — anything about saving toward a specific goal",
    "capital_gains": "Capital gains tax, LTCG, STCG, selling shares/property/gold — anything about tax on sale of assets",
    "hike":          "Salary hike, appraisal, job switch, new offer comparison — anything about salary increase impact",
    "compare":       "Comparison between financial options (X vs Y), which is better, pros/cons — any decision-making/comparison query",
}

# Minimum topics for LLM fallback to trigger (if regex finds fewer than this, ask LLM)
_LLM_FALLBACK_THRESHOLD = 1


def _extract_numbers(text: str) -> list[float]:
    """Extract all numbers with Indian notation support."""
    t = text.lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs ", " ")
    results = []
    mag_pat = re.compile(
        r'(\d+\.?\d*)\s*'
        r'(crores?|cr|lakhs?|lacs?|lpa|lac|thousands?|[lkc])'
        r'(?![a-zA-Z])', re.IGNORECASE
    )
    consumed = set()
    for m in mag_pat.finditer(t):
        num = float(m.group(1))
        unit = m.group(2).lower()
        if unit.startswith("cr") or unit == "c":
            results.append(num * 10000000)
        elif unit in ("lpa",) or unit.startswith("la") or unit == "l":
            results.append(num * 100000)
        elif unit.startswith("th") or unit == "k":
            results.append(num * 1000)
        consumed.add((m.start(), m.end()))

    for m in re.finditer(r'(\d+\.?\d*)', t):
        if not any(m.start() >= s and m.end() <= e for s, e in consumed):
            num = float(m.group(1))
            if num > 0:
                results.append(num)
    return results


def _detect_income(numbers: list[float], query: str) -> Optional[float]:
    """Identify the income number from extracted numbers."""
    q = query.lower()
    has_annual = any(w in q for w in ["ctc", "lpa", "per annum", "annual", "package", "per year"])
    has_monthly = any(w in q for w in ["monthly", "per month", "in-hand", "take home"])
    has_income_word = any(w in q for w in ["earn", "salary", "income", "ctc", "lpa", "package"])

    # Words that mark a number as NOT income
    non_income_words = ["loan", "emi", "property", "house", "flat", "rent", "invest",
                        "prepay", "goal", "wedding", "car", "education", "corpus",
                        "insurance", "cover", "premium", "gold", "fd", "ppf", "buy"]

    for n in numbers:
        if has_annual and n >= 100000:
            return n  # Annual CTC
        if has_monthly and 10000 <= n <= 1000000:
            return n * 12  # Convert monthly to annual

    # Fallback: only if there's an income-related word in the query
    if has_income_word:
        for n in numbers:
            if n >= 300000:
                return n
    return None


def _detect_topics(query: str) -> set:
    """
    HYBRID topic detection: Fast regex → LLM reasoning fallback.

    Layer 1 — Direct keywords (0ms): Unambiguous domain terms
    Layer 2 — Life event inference (0ms): Connects related financial domains
    Layer 3 — LLM fallback (~1-2s): Only invoked when regex finds ≤1 topic
              on ambiguous/natural-language queries. Uses the model's reasoning
              to pick relevant calculators from the full registry.

    This gives instant results for clear queries ("SIP calculator", "EMI for 50L")
    and intelligent classification for vague ones ("what should I do with 10 lakhs?",
    "just got married, help me plan").
    """
    q = query.lower()
    words = set(re.findall(r'\b\w+\b', q))
    topics = set()

    # ════════════════ LAYER 1: Direct Keywords (instant) ════════════════
    # Technical/domain-specific terms that unambiguously map to a topic
    keyword_map = {
        "tax":           {"tax", "80c", "80d", "deduction", "itr", "tds", "regime"},
        "salary":        {"salary", "ctc", "lpa", "package", "pf", "gratuity", "epf"},
        "loan":          {"loan", "emi", "emis", "mortgage", "borrow", "debt"},
        "prepay":        {"prepay", "prepayment", "foreclose"},
        "invest":        {"sip", "elss", "nifty", "equity", "portfolio", "nfo", "invest", "investing", "investment"},
        "retirement":    {"retirement", "pension", "nps", "superannuation", "retire", "corpus"},
        "insurance":     {"insurance", "lic", "mediclaim"},
        "budget":        {"budget", "50/30/20"},
        "hra":           {"hra"},
        "property":      {"property", "apartment", "flat"},
        "gold":          {"gold", "sgb"},
        "fd":            {"fd"},
        "ppf":           {"ppf"},
        "rd":            {"rd"},
        "ssy":           {"ssy", "sukanya"},
        "nps":           {"nps"},
        "nsc":           {"nsc"},
        "scss":          {"scss"},
        "gst":           {"gst"},
        "gratuity":      {"gratuity"},
        "epf":           {"epf"},
        "kvp":           {"kvp"},
        "swp":           {"swp"},
        "apy":           {"apy"},
        "crypto":        {"crypto", "bitcoin", "btc", "ethereum", "eth", "web3"},
        "education":     {"college", "abroad"},
        "goal":          {"goal", "target"},
        "capital_gains": {"ltcg", "stcg"},
        "hike":          {"appraisal", "promoted", "promotion", "hike"},
    }
    for topic, kws in keyword_map.items():
        if words & kws:
            topics.add(topic)

    # Multi-word phrase matches
    phrase_map = {
        "tax":           ["income tax", "old regime", "new regime", "80c", "80d", "tax saving", "tax slab", "what about tax"],
        "salary":        ["take home", "take-home", "in-hand", "in hand", "cost to company", "ctc break", r"earn\w*\s+\d", r"\d+\s*lpa"],
        "loan":          ["home loan", "car loan", "personal loan", "education loan"],
        "prepay":        ["pre-pay", "part payment", "lump sum payment", "close.*early", "pay off.*loan", "pay.*off.*debt", "debt.?free"],
        "invest":        ["mutual fund", "index fund", "stock market", "share market", "where.*invest", "want.*invest", r"grow.*(?:wealth|money)", r"(?:wealth|money).*grow", "idle money", r"build.*(?:wealth|corpus)"],
        "retirement":    ["old age", "retire early", r"(?:how much|need).*retire", "fire movement", r"(?:after|post)\s+(?:60|65)", r"retire\s+(?:comfortabl|peacefull)"],
        "insurance":     ["term plan", "term life", "health insurance", "life cover", r"protect.*famil", r"famil.*(?:protect|secur|safe|cover)", r"(?:medical|health).*(?:cover|expense)", "what if.*(?:die|pass|something happen)", r"(?:cover|safe).*(?:wife|husband|kids|children|dependents|parents|family)"],
        "budget":        ["emergency fund"],
        "hra":           ["house rent", "rent allowance", "rent exemption"],
        "property":      ["real estate", "rent vs buy", "buy vs rent", r"(?:buy|purchase|own).*(?:house|home|flat|place|apartment|villa)", r"(?:house|home|flat|apartment).*(?:buy|purchase|own)", "first home", "place of my own"],
        "gold":          ["sovereign gold", "gold bond", "gold etf", "digital gold"],
        "fd":            ["fixed deposit", "bank deposit"],
        "rd":            ["recurring deposit"],
        "ppf":           ["public provident", "provident fund"],
        "ssy":           ["sukanya samriddhi", "girl child", "beti bachao"],
        "nps":           ["national pension", "pension system", "pension scheme"],
        "nsc":           ["national savings certificate", "savings certificate"],
        "scss":          ["senior citizen.*sav", "scss scheme"],
        "gst":           ["goods and service", "goods & service", "gst rate", "gst calc"],
        "gratuity":      ["gratuity calc", "years of service.*gratuit", "gratuit.*years"],
        "epf":           ["employee.*provident", "provident fund", "pf balance", "pf calc"],
        "kvp":           ["kisan vikas", "kvp double"],
        "swp":           ["systematic withdrawal", "withdrawal plan", "regular income.*corpus"],
        "apy":           ["atal pension", "pension yojana"],
        "education":     ["child education", "abroad study", "ms abroad", "kids school"],
        "goal":          ["plan for", "planning for", "save for", "saving for"],
        "capital_gains": ["capital gain", "sell shares", "book profit", "tax on sale", "profit on", r"sold.*(?:share|stock|mutual|property|flat|house|gold|crypto|bitcoin)", r"(?:sell|selling).*(?:share|stock|mutual|property|flat|house|gold|crypto)"],
        "hike":          ["new offer", "switch job", "job change", "job switch", r"(?:raise|jump|hike).*(?:salary|ctc|pay)", r"(?:salary|ctc|pay).*(?:raise|jump|hike)", "counter.?offer", r"\d+%.*hike", r"hike.*\d+%"],
        "compare":       ["vs", "versus", "or", "which.*better", "should i", "pros and cons"],
    }
    for topic, phrases in phrase_map.items():
        if topic not in topics:
            if any(re.search(p, q) for p in phrases):
                topics.add(topic)

    # ════════════════ LAYER 2: Life Event Inference (instant) ════════════════
    # Detect life events and auto-add ALL related financial domains
    life_events = {
        "marriage":       bool(re.search(r'\b(?:married|marriage|wedding|engaged|engagement|spouse|wife|husband)\b', q)),
        "new_baby":       bool(re.search(r'\b(?:baby|pregnant|expecting|newborn|child\s*birth|new\s*born|toddler|infant)\b', q)),
        "job_loss":       bool(re.search(r'\b(?:lost\s+(?:my\s+)?job|laid\s+off|fired|unemploy|retrench|jobless|no\s+income)\b', q)),
        "job_switch":     bool(re.search(r'\b(?:new\s+(?:job|offer|company)|switch(?:ing|ed)?\s+(?:job|company)|counter\s*offer|joining|resign)\b', q)),
        "windfall":       bool(re.search(r'\b(?:bonus|inheritance|windfall|lump\s*sum|gift|maturity|settlement|arrears|got\s+\d+\s*(?:l|lakh|cr|crore))\b', q)),
        "buying_home":    bool(re.search(r'\b(?:buy|buying|purchase|purchasing)\b.*\b(?:house|home|flat|apartment|property|villa)\b', q)),
        "crisis":         bool(re.search(r'\b(?:emergency|crisis|urgent|desperate|critical|broke|bankrupt|stress(?:ed)?)\b', q)),
        "health_issue":   bool(re.search(r'\b(?:hospital|surgery|medical\s+emergency|diagnosed|illness|disease|treatment)\b', q)),
        "child_edu":      bool(re.search(r'\b(?:kids?|child(?:ren)?|son|daughter)\b.*\b(?:school|college|education|study|future|abroad|coaching)\b', q)),
        "near_retirement": bool(re.search(r'\b(?:retir(?:ing|e)\s+(?:soon|next|in\s+\d)|(?:55|56|57|58|59|60)\s*(?:year|yr).*(?:old|age))\b', q)),
    }

    inference_map = {
        "marriage":        {"goal", "budget", "insurance", "tax"},
        "new_baby":        {"insurance", "budget", "goal", "education"},
        "job_loss":        {"budget", "insurance"},
        "job_switch":      {"salary", "hike", "tax", "compare"},
        "windfall":        {"invest", "compare", "tax"},
        "buying_home":     {"property", "loan", "budget", "insurance"},
        "crisis":          {"budget"},
        "health_issue":    {"insurance", "budget"},
        "child_edu":       {"education", "goal", "invest"},
        "near_retirement": {"retirement", "insurance", "invest"},
    }

    detected_events = []
    for event, triggered in life_events.items():
        if triggered:
            detected_events.append(event)
            topics.update(inference_map.get(event, set()))

    # Context-aware implications (instant)
    if "loan" in topics and any(int(n) >= 500000 for n in re.findall(r'\d+', q) if len(n) >= 6):
        topics.add("budget")
    if "property" in topics and "loan" not in topics:
        topics.add("loan")
    if "invest" in topics and "compare" not in topics:
        if re.search(r'\b(?:which|what|should|where|how|best|better)\b', q):
            topics.add("compare")
    if "windfall" in detected_events and "loan" in topics:
        topics.add("prepay")
        topics.add("compare")

    # Combo: buy + rent → property + compare
    buy_words = {"buy", "buying", "purchase", "purchasing", "own", "owning"}
    rent_words = {"rent", "renting", "tenant", "tenancy"}
    if (words & buy_words) and (words & rent_words):
        topics.add("property")
        topics.add("compare")

    # ════════════════ LAYER 3: LLM Reasoning Fallback ════════════════
    # Only fires when regex found very few topics — means the query is
    # ambiguous or uses natural language the regex can't catch.
    # The LLM reads the query and picks topics using its reasoning ability.
    if len(topics) <= _LLM_FALLBACK_THRESHOLD:
        llm_topics = _llm_classify_topics(query, topics)
        if llm_topics:
            topics.update(llm_topics)
            logger.info(f"LLM fallback added topics: {llm_topics} (regex had: {topics - llm_topics})")

    return topics


def _llm_classify_topics(query: str, existing_topics: set) -> set:
    """
    Use the LLM to classify which calculator topics are relevant.
    Only called as fallback when regex detection finds ≤1 topic.
    Uses a short, focused prompt for fast inference (~1-2s).
    """
    try:
        from llm.engine import llm
        if not llm._initialized:
            # Don't block startup — LLM not ready yet
            logger.debug("LLM not initialized, skipping fallback classification")
            return set()

        # Build a concise prompt listing available topics
        topic_list = "\n".join(f"- {k}: {v}" for k, v in CALC_TOPIC_REGISTRY.items())
        prompt = (
            f"Given this financial query, pick ALL relevant calculator topics from the list below.\n"
            f"Think about what a financial advisor would compute for this query.\n"
            f"Reply with ONLY the topic keys as a comma-separated list. Nothing else.\n\n"
            f"Available topics:\n{topic_list}\n\n"
            f"Query: \"{query}\"\n\n"
            f"Relevant topics:"
        )

        response = llm.model.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a financial query classifier. Pick calculator topics relevant to the user's financial query. Reply with ONLY comma-separated topic keys. /no_think"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=100,
            top_p=0.9,
        )

        raw = response["choices"][0]["message"]["content"].strip()
        # Strip any think tags that Qwen3 might produce
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
        # Parse comma-separated topic keys
        valid_keys = set(CALC_TOPIC_REGISTRY.keys())
        llm_topics = set()
        for token in re.split(r'[,\s]+', raw):
            token = token.strip().lower().replace('"', '').replace("'", "")
            if token in valid_keys:
                llm_topics.add(token)

        logger.info(f"LLM classified topics: {llm_topics} (raw: {raw[:80]})")
        return llm_topics

    except Exception as e:
        logger.warning(f"LLM topic classification failed: {e}")
        return set()


def _detect_sentiment(query: str) -> dict:
    """
    Detect user's emotional state and urgency.
    Returns a dict with sentiment signals that affect calculator behavior.
    """
    q = query.lower()
    sentiment = {
        "urgency": "normal",     # normal, urgent, crisis
        "emotion": "neutral",    # neutral, anxious, excited, confused, overwhelmed
        "risk_comfort": "moderate",  # conservative, moderate, aggressive
        "life_stage": None,      # young_professional, mid_career, pre_retirement, retired
    }

    # Urgency
    if re.search(r'\b(?:urgent|immediately|asap|right\s+now|emergency|desperate|crisis|critical)\b', q):
        sentiment["urgency"] = "crisis"
    elif re.search(r'\b(?:soon|quickly|fast|hurry|deadline|this\s+month|this\s+week)\b', q):
        sentiment["urgency"] = "urgent"

    # Emotion
    if re.search(r'\b(?:worried|worrying|anxious|scared|afraid|fear\w*|nervous|stress\w*|tension|panic\w*|sleepless|lost\s+(?:my\s+)?job)\b', q):
        sentiment["emotion"] = "anxious"
    elif re.search(r'\b(?:too\s+much|overwhelm\w*|so\s+many|can.t\s+handle|drown\w*)\b', q):
        sentiment["emotion"] = "overwhelmed"
    elif re.search(r'\b(?:confus\w*|unsure|don.t\s+know|no\s+idea|clueless|help\s+me|what\s+(?:do|should))\b', q):
        sentiment["emotion"] = "confused"
    elif re.search(r'\b(?:excit\w*|happy|great|amazing|thrilled|pumped|awesome|yay|ready)\b', q):
        sentiment["emotion"] = "excited"
    elif re.search(r'\b(?:frustrat\w*|angry|annoy\w*|fed\s+up|sick\s+of|tired\s+of|waste)\b', q):
        sentiment["emotion"] = "frustrated"

    # Risk comfort (inferred from language)
    if re.search(r'\b(?:safe|secure|guaranteed|risk\s*free|no\s+risk|protect|conserv|stable|sure)\b', q):
        sentiment["risk_comfort"] = "conservative"
    elif re.search(r'\b(?:aggressive|high\s+return|maximum|risk|yolo|bet|bold|multiply)\b', q):
        sentiment["risk_comfort"] = "aggressive"

    # Life stage (from age or context)
    age_m = re.search(r'\b(?:i\s+am|i.m|age\s*(?:is)?)\s*(\d{2})\b', q)
    if not age_m:
        age_m = re.search(r'\b(\d{2})\s*(?:years?\s*old|yrs?\s*old|yo|y/o)\b', q)
    if age_m:
        age = int(age_m.group(1))
        if age < 30:
            sentiment["life_stage"] = "young_professional"
        elif age < 45:
            sentiment["life_stage"] = "mid_career"
        elif age < 58:
            sentiment["life_stage"] = "pre_retirement"
        else:
            sentiment["life_stage"] = "retired"

    return sentiment


def smart_calculate(query: str, profile: dict = None) -> str:
    """
    Analyse query and auto-run ALL relevant calculators.
    Returns a pre-computed context block for the LLM.

    The LLM's job is to EXPLAIN and ADVISE — not to compute.
    """
    from tools.financial_calc import (
        ctc_to_take_home, tax_bracket_india, hra_exemption,
        sip_calculator, stepup_sip, goal_sip, lumpsum_vs_sip,
        emi_calculator, loan_prepayment, rent_vs_buy,
        retirement_corpus, fire_calculator,
        compound_interest, inflation_adjusted_return, inflation_goal_planner,
        emergency_fund, insurance_coverage, ppf_calculator, fd_calculator,
        education_loan_calc, capital_gains_tax, section_80c_optimizer,
        salary_hike_impact, debt_to_income, savings_rate,
    )
    from agents.base import fmt_inr

    if profile is None:
        profile = {}

    numbers = _extract_numbers(query)
    topics = _detect_topics(query)
    sentiment = _detect_sentiment(query)
    income = _detect_income(numbers, query)

    # Also check profile for income and age
    if not income and profile.get("income"):
        prof_nums = _extract_numbers(profile["income"])
        if prof_nums:
            income = prof_nums[0]

    # Enrich sentiment from profile
    if not sentiment["life_stage"] and profile.get("age"):
        try:
            age = int(profile["age"])
            if age < 30: sentiment["life_stage"] = "young_professional"
            elif age < 45: sentiment["life_stage"] = "mid_career"
            elif age < 58: sentiment["life_stage"] = "pre_retirement"
            else: sentiment["life_stage"] = "retired"
        except (ValueError, TypeError):
            pass

    results = []
    computed = set()

    def add(label, text):
        results.append(f"[{label}]\n{text}")

    # ═══════════════════ SALARY / CTC ═══════════════════
    if income and income >= 100000 and topics & {"salary", "tax", "budget", "retirement", "loan", "invest", "insurance", "hike", "hra"}:
        data = ctc_to_take_home(income)
        computed.add("ctc")
        # Determine EPF type for display
        epf_note = "on full Basic" if data.get("epf_on_full_basic") else f"capped at {fmt_inr(data['epf_wage_ceiling'])}/yr"
        add("SALARY BREAKDOWN", (
            f"CTC: {fmt_inr(income)}/yr\n"
            f"\n── Monthly Structure ──\n"
            f"Basic: {fmt_inr(data['basic_monthly'])}/mo ({data['basic_pct']}% of CTC)\n"
            f"HRA: {fmt_inr(data.get('hra_monthly', data['hra'] // 12))}/mo\n"
            f"Special Allowance: {fmt_inr(data.get('special_allowance_monthly', data['special_allowance'] // 12))}/mo\n"
            f"Gross Salary: {fmt_inr(data.get('gross_monthly', data['gross_salary'] // 12))}/mo = {fmt_inr(data['gross_salary'])}/yr\n"
            f"\n── PF (Provident Fund) Details ──\n"
            f"EPF Employee (12%): {fmt_inr(data.get('epf_employee_monthly', data['epf_employee'] // 12))}/mo = {fmt_inr(data['epf_employee'])}/yr ({epf_note})\n"
            f"EPF Employer (12%): {fmt_inr(data.get('epf_employer_monthly', data['epf_employer_total'] // 12))}/mo = {fmt_inr(data['epf_employer_total'])}/yr\n"
            f"  → To EPF account: {fmt_inr(data['epf_employer_epf'])}/yr\n"
            f"  → To EPS (Pension): {fmt_inr(data['eps_contribution'])}/yr ({fmt_inr(data.get('eps_monthly', data['eps_contribution'] // 12))}/mo, capped at ₹1,250/mo)\n"
            f"Total PF accumulation: {fmt_inr(data['epf_employee'] + data['epf_employer_total'])}/yr (employee + employer)\n"
            f"EPF auto-qualifies for 80C: {fmt_inr(data.get('section_80c_auto_epf', min(data['epf_employee'], 150000)))}\n"
            f"\n── Gratuity ──\n"
            f"Annual provision: {fmt_inr(data['gratuity_annual_provision'])}/yr ({fmt_inr(data.get('gratuity_monthly_provision', data['gratuity_annual_provision'] // 12))}/mo)\n"
            f"Gratuity after 5yr: {fmt_inr(data.get('gratuity_5yr', 0))} | 10yr: {fmt_inr(data.get('gratuity_10yr', 0))} | 20yr: {fmt_inr(data.get('gratuity_20yr', 0))}\n"
            f"Tax exempt up to ₹20,00,000 (Section 10(10)) | Eligible after 5 years service\n"
            f"\n── Tax Comparison ──\n"
            f"Tax (New Regime): {fmt_inr(data['tax_new_regime'])}/yr ({fmt_inr(data.get('tax_new_monthly', data['tax_new_regime'] // 12))}/mo, eff {data['effective_tax_rate_new']}%)"
            + (" — ZERO TAX (87A rebate)" if data.get('rebate_new') else "") + "\n"
            f"Tax (Old Regime): {fmt_inr(data['tax_old_regime'])}/yr ({fmt_inr(data.get('tax_old_monthly', data['tax_old_regime'] // 12))}/mo, eff {data['effective_tax_rate_old']}%)"
            + (" — ZERO TAX (87A rebate)" if data.get('rebate_old') else "") + "\n"
            f"  Old regime: 80C deduction of {fmt_inr(data.get('section_80c_total', 0))} applied (EPF auto + others)\n"
            f"  80C room left: {fmt_inr(data.get('section_80c_remaining', 0))} → invest in ELSS/PPF for more savings\n"
            f"\n── Take-Home Pay ──\n"
            f"Deductions/mo (New): EPF {fmt_inr(data.get('epf_employee_monthly', data['epf_employee'] // 12))} + PT {fmt_inr(data.get('professional_tax_monthly', 200))} + Tax {fmt_inr(data.get('tax_new_monthly', data['tax_new_regime'] // 12))} = {fmt_inr(data.get('total_deductions_monthly_new', 0))}/mo\n"
            f"Take-home (New): {fmt_inr(data['take_home_monthly_new'])}/mo = {fmt_inr(data['take_home_annual_new'])}/yr\n"
            f"Take-home (Old): {fmt_inr(data['take_home_monthly_old'])}/mo = {fmt_inr(data['take_home_annual_old'])}/yr\n"
            f"Better regime: {'New' if data['tax_new_regime'] <= data['tax_old_regime'] else 'Old'} (saves {fmt_inr(abs(data['tax_new_regime'] - data['tax_old_regime']))})\n"
            f"\n── Retirement Accrual ──\n"
            f"EPF (yours + employer): {fmt_inr(data['epf_employee'] + data['epf_employer_total'])}/yr\n"
            f"Gratuity provision: {fmt_inr(data['gratuity_annual_provision'])}/yr\n"
            f"Total retirement benefit: {fmt_inr(data['total_retirement_annual'])}/yr ({fmt_inr(data.get('total_retirement_monthly', data['total_retirement_annual'] // 12))}/mo)"
        ))
        monthly_takehome = data["take_home_monthly_new"]

    # ═══════════════════ SALARY HIKE IMPACT ═══════════════════
    if income and "hike" in topics:
        hike_data = salary_hike_impact(income)
        computed.add("hike")
        lines = [f"Current: CTC {fmt_inr(income)}, Take-home {fmt_inr(hike_data['current_monthly_takehome'])}/mo"]
        for s in hike_data["scenarios"]:
            lines.append(
                f"  {s['hike_pct']}% hike → CTC {fmt_inr(s['new_ctc'])}, "
                f"Take-home {fmt_inr(s['new_monthly_takehome'])}/mo "
                f"(+{fmt_inr(s['takehome_increase'])}, effective hike {s['effective_hike_pct']}%)"
            )
        lines.append(hike_data["insight"])
        add("SALARY HIKE ANALYSIS", "\n".join(lines))

    # ═══════════════════ HRA EXEMPTION ═══════════════════
    if "hra" in topics and income:
        basic_annual = income * 0.50
        hra_recv = basic_annual * 0.50
        # Try to find rent amount
        rent_amounts = [n for n in numbers if 3000 <= n <= 200000]
        if rent_amounts:
            rent_monthly = rent_amounts[0]
            rent_annual = rent_monthly * 12 if rent_monthly < 200000 else rent_monthly
        else:
            rent_annual = basic_annual * 0.30  # Assume rent = 30% of basic
        metro = not any(w in query.lower() for w in ["non-metro", "tier 2", "tier-2", "tier 3"])
        hra_data = hra_exemption(basic_annual, hra_recv, rent_annual, metro)
        computed.add("hra")
        add("HRA EXEMPTION (Old Regime)", (
            f"Basic: {fmt_inr(basic_annual)}/yr | HRA received: {fmt_inr(hra_recv)}/yr\n"
            f"Rent paid: {fmt_inr(rent_annual)}/yr | City: {'Metro' if metro else 'Non-metro'}\n"
            f"Option 1 (Actual HRA): {fmt_inr(hra_data['option1_actual_hra'])}\n"
            f"Option 2 (Rent − 10% Basic): {fmt_inr(hra_data['option2_rent_minus_10pct'])}\n"
            f"Option 3 ({'50' if metro else '40'}% of Basic): {fmt_inr(hra_data['option3_50_or_40_pct_basic'])}\n"
            f"EXEMPT: {fmt_inr(hra_data['hra_exemption'])} | TAXABLE: {fmt_inr(hra_data['taxable_hra'])}"
        ))

    # ═══════════════════ TAX OPTIMIZATION ═══════════════════
    if "tax" in topics and income and "ctc" in computed:
        data = ctc_to_take_home(income)
        opt = section_80c_optimizer(
            epf_employee=data["epf_employee"],
            ppf=0, elss=0, life_insurance=0,
        )
        computed.add("tax_opt")
        suggestions_text = " | ".join(opt["suggestions"][:3]) if opt["suggestions"] else "Maximize 80C"
        add("TAX OPTIMIZATION (Old Regime)", (
            f"80C used: {fmt_inr(opt['section_80c']['total_claimed'])} of ₹1.5L limit\n"
            f"  EPF (auto-80C): {fmt_inr(opt['section_80c']['epf'])}\n"
            f"  Unused 80C: {fmt_inr(opt['section_80c']['unused'])} → invest in ELSS/PPF\n"
            f"80CCD(1B) NPS: {fmt_inr(opt['section_80ccd1b_nps'])} of ₹50K\n"
            f"Total deductions available: {fmt_inr(opt['total_deductions'])}\n"
            f"Estimated tax saving: {fmt_inr(opt['estimated_tax_saved'])}\n"
            f"Action: {suggestions_text}"
        ))

    # Initialize loan_amt for cross-section reference
    loan_amt = None

    # ═══════════════════ LOAN / EMI ═══════════════════
    if topics & {"loan", "prepay"}:
        # Find loan amount — use context clues to disambiguate
        q = query.lower()

        # Strategy: look for number near "loan" keyword for loan amount,
        # and number near "prepay"/"extra"/"lumpsum" for prepay amount.
        # Fallback: largest number = loan, second largest = prepay.
        candidate_nums = [n for n in numbers if n >= 100000 and (not income or n != income)]

        # Try context-based matching: "40 lakh loan" → 40L is loan
        loan_context = re.search(
            r'(\d+\.?\d*)\s*(?:crores?|cr|lakhs?|lacs?|lac|[lkc])\s*(?:home\s+)?(?:loan|mortgage|emi|borrow)',
            q
        )
        prepay_context = re.search(
            r'(\d+\.?\d*)\s*(?:crores?|cr|lakhs?|lacs?|lac|[lkc])\s*(?:prepay|pre-pay|extra|lump\s*sum|part\s*pay|prepayment)',
            q
        )
        # Also match "prepay 5 lakhs"
        if not prepay_context:
            prepay_context = re.search(
                r'(?:prepay|pre-pay|extra|lump\s*sum|part\s*pay)\s*(?:of\s+)?(?:₹|rs\.?\s*)?(\d+\.?\d*)\s*(?:crores?|cr|lakhs?|lacs?|lac|[lkc])?',
                q
            )

        if loan_context:
            num_for_loan = float(loan_context.group(1))
            loan_amt = next((n for n in candidate_nums if abs(n / (num_for_loan * 100000) - 1) < 0.01 or abs(n / (num_for_loan * 10000000) - 1) < 0.01 or abs(n - num_for_loan) < 1), None)
        if not loan_amt and candidate_nums:
            # If the only candidate number matches a prepay context, don't use it as loan amount
            if prepay_context and len(candidate_nums) == 1:
                prepay_num = float(prepay_context.group(1))
                candidate_val = candidate_nums[0]
                # Check if the only candidate matches the prepay number
                if abs(candidate_val / (prepay_num * 100000) - 1) < 0.01 or abs(candidate_val / (prepay_num * 10000000) - 1) < 0.01 or abs(candidate_val - prepay_num) < 1:
                    loan_amt = None  # Don't treat prepay amount as loan
                else:
                    loan_amt = max(candidate_nums)
            else:
                # Largest number is most likely the loan amount
                loan_amt = max(candidate_nums)

        if loan_amt:
            # Detect loan type for appropriate rate
            if "home" in q or "house" in q or "property" in q:
                rates = [8.25, 8.50, 9.00]
                tenures = [15, 20, 25]
            elif "car" in q or "vehicle" in q:
                rates = [8.50, 9.00, 10.00]
                tenures = [5, 7]
            elif "education" in q or "study" in q:
                rates = [8.00, 9.50, 11.00]
                tenures = [7, 10]
            elif "personal" in q:
                rates = [10.50, 12.00, 14.00]
                tenures = [3, 5]
            else:
                rates = [8.50, 9.50, 10.50]
                tenures = [10, 15, 20]

            computed.add("loan")
            lines = [f"Loan amount: {fmt_inr(loan_amt)}"]
            for rate in rates:
                for tenure in tenures[:2]:
                    emi_data = emi_calculator(loan_amt, rate, tenure * 12)
                    lines.append(
                        f"  @{rate}% × {tenure}yr: EMI {fmt_inr(emi_data['emi'])}/mo, "
                        f"Total interest: {fmt_inr(emi_data['total_interest'])}"
                    )
            add("LOAN EMI TABLE", "\n".join(lines))

            # Affordability check
            if income and "ctc" in computed:
                monthly_th = ctc_to_take_home(income)["take_home_monthly_new"]
                max_emi_safe = monthly_th * 0.40
                max_emi_stretch = monthly_th * 0.50
                lines2 = [
                    f"Take-home: {fmt_inr(monthly_th)}/mo",
                    f"Safe EMI (40%): {fmt_inr(max_emi_safe)}/mo",
                    f"Stretch EMI (50%): {fmt_inr(max_emi_stretch)}/mo",
                ]
                mid_rate = rates[1]
                mid_tenure = tenures[-1]
                mid_emi = emi_calculator(loan_amt, mid_rate, mid_tenure * 12)["emi"]
                if mid_emi > max_emi_stretch:
                    lines2.append(f"⚠️ EMI {fmt_inr(mid_emi)} EXCEEDS safe limit — HIGH RISK")
                elif mid_emi > max_emi_safe:
                    lines2.append(f"⚠️ EMI {fmt_inr(mid_emi)} is in stretched zone — manageable but tight")
                else:
                    lines2.append(f"✅ EMI {fmt_inr(mid_emi)} is within safe limit")
                add("AFFORDABILITY CHECK", "\n".join(lines2))

        # Prepayment analysis
        if "prepay" in topics and loan_amt:
            # Context-aware prepay amount detection
            prepay = None
            # First: try context-matched prepay amount from regex above
            if prepay_context:
                prepay_num = float(prepay_context.group(1))
                # Match against extracted numbers (it could be in lakhs, crores etc)
                for n in numbers:
                    if n != loan_amt and (not income or n != income):
                        if abs(n / (prepay_num * 100000) - 1) < 0.01 or abs(n / (prepay_num * 10000000) - 1) < 0.01 or abs(n - prepay_num) < 1:
                            prepay = n
                            break
            # Second: find any number that's not the loan amount or income
            if not prepay:
                prepay_amts = [n for n in numbers if n != loan_amt and n >= 10000 and (not income or n != income)]
                prepay = prepay_amts[0] if prepay_amts else None
            # Third: if "compare" topic (prepay vs invest), the non-loan number is the amount for BOTH
            if not prepay and "compare" in topics:
                # When someone says "should I prepay loan or invest?", default to 10% of loan
                prepay = loan_amt * 0.10
            elif not prepay:
                prepay = loan_amt * 0.10

            rate_mid = rates[1] if 'rates' in dir() else 8.5
            tenure_mid = (tenures[-1] if 'tenures' in dir() else 20) * 12
            for strategy in ["tenure", "emi"]:
                pp = loan_prepayment(loan_amt, rate_mid, tenure_mid, prepay, reduce=strategy)
                add(f"PREPAYMENT ({strategy.upper()})", (
                    f"Prepay {fmt_inr(prepay)} after 12 months (strategy: reduce {strategy})\n"
                    f"Original EMI: {fmt_inr(pp['original_emi'])} | Original interest: {fmt_inr(pp['original_total_interest'])}\n"
                    f"Interest saved: {fmt_inr(pp['interest_saved'])}"
                    + (f" | Months saved: {pp['months_saved']} ({pp['years_saved']}yr)" if strategy == "tenure" else "")
                    + (f" | New EMI: {fmt_inr(pp['new_emi'])} (↓{fmt_inr(pp['emi_reduction'])})" if strategy == "emi" else "")
                ))

    # ═══════════════════ INVESTMENT / SIP ═══════════════════
    if topics & {"invest", "retirement", "goal", "budget"}:
        # Determine SIP amount
        sip_amt = None
        for n in sorted(numbers):
            if 500 <= n <= 500000 and (not income or n != income):
                sip_amt = n
                break
        if not sip_amt and income:
            monthly_th = ctc_to_take_home(income)["take_home_monthly_new"]
            sip_amt = round(monthly_th * 0.20 / 500) * 500  # 20% of take-home, rounded to 500

        if sip_amt and sip_amt >= 500:
            computed.add("sip")
            # Flat SIP
            lines = [f"Monthly SIP: {fmt_inr(sip_amt)}"]
            for rate in [10, 12, 14]:
                for yr in [5, 10, 20, 30]:
                    s = sip_calculator(sip_amt, rate, yr)
                    lines.append(f"  @{rate}% × {yr}yr: Corpus {fmt_inr(s['future_value'])} (invested {fmt_inr(s['total_invested'])})")
            add("SIP PROJECTIONS", "\n".join(lines))

            # Step-up SIP
            su = stepup_sip(sip_amt, 12.0, 20, 10.0)
            add("STEP-UP SIP (10% annual increase)", (
                f"Start: {fmt_inr(sip_amt)}/mo → Year 20: {fmt_inr(su['final_monthly_sip'])}/mo\n"
                f"Corpus: {fmt_inr(su['final_corpus'])} (vs flat SIP: {fmt_inr(su['flat_sip_corpus'])})\n"
                f"Step-up advantage: +{fmt_inr(su['stepup_advantage'])} ({su['stepup_advantage_pct']}% more)"
            ))

        # Lumpsum vs SIP — useful when user has a lump sum to deploy
        lumpsum_amt = None
        if "compare" in topics or "prepay" in topics:
            # Find a lumpsum amount (not income, not loan)
            for n in sorted(numbers, reverse=True):
                if n >= 50000 and (not income or n != income) and (not loan_amt or n != loan_amt):
                    lumpsum_amt = n
                    break
        if lumpsum_amt:
            computed.add("lumpsum")
            ls = lumpsum_vs_sip(lumpsum_amt, 12.0, 10)
            add("LUMPSUM vs SIP COMPARISON", (
                f"Amount: {fmt_inr(lumpsum_amt)} @12% for 10yr\n"
                f"Lumpsum: {fmt_inr(ls['lumpsum_value'])} | SIP: {fmt_inr(ls['sip_value'])}\n"
                f"Lumpsum advantage: {fmt_inr(ls['lumpsum_advantage'])}\n"
                f"{ls['verdict']}"
            ))

    # ═══════════════════ GOAL PLANNING ═══════════════════
    if "goal" in topics:
        # Try to find goal amount and timeline
        goal_amt = None
        goal_years = None
        for n in numbers:
            if n >= 100000 and (not income or n != income):
                goal_amt = n
            elif 1 <= n <= 40:
                goal_years = int(n)

        if goal_amt:
            goal_years = goal_years or 10
            # Inflation-adjusted goal
            ig = inflation_goal_planner(goal_amt, goal_years)
            computed.add("goal")
            add("GOAL PLANNING", (
                f"Goal today: {fmt_inr(goal_amt)} | In {goal_years} years: {fmt_inr(ig['future_cost'])} (with {ig['inflation_rate']}% inflation)\n"
                f"SIP needed @10%: {fmt_inr(ig['sip_needed']['sip_at_10pct'])}/mo\n"
                f"SIP needed @12%: {fmt_inr(ig['sip_needed']['sip_at_12pct'])}/mo\n"
                f"SIP needed @14%: {fmt_inr(ig['sip_needed']['sip_at_14pct'])}/mo"
            ))

    # ═══════════════════ RETIREMENT ═══════════════════
    if "retirement" in topics:
        # Estimate monthly expenses
        if income and "ctc" in computed:
            monthly_th = ctc_to_take_home(income)["take_home_monthly_new"]
            monthly_exp = round(monthly_th * 0.55)  # ~55% of take-home = expenses
        elif profile.get("expenses"):
            exp_nums = _extract_numbers(profile["expenses"])
            monthly_exp = exp_nums[0] if exp_nums else 50000
        else:
            monthly_exp = 50000

        # Detect age
        age = None
        age_m = re.search(r'\b(?:i am|i.m|age\s*(?:is)?)\s*(\d{2})\b', query.lower())
        if not age_m:
            age_m = re.search(r'\b(\d{2})\s*(?:years?\s*old|yrs?\s*old)\b', query.lower())
        if age_m:
            age = int(age_m.group(1))
        elif profile.get("age"):
            age = int(profile["age"])

        retire_age = 60
        current_age = age or 30
        years_to_retire = max(1, retire_age - current_age)

        computed.add("retirement")
        ret = retirement_corpus(monthly_exp, 6.0, years_to_retire, 30, 12.0)
        add("RETIREMENT CORPUS", (
            f"Age: {current_age} | Retire at: {retire_age} | Years: {years_to_retire}\n"
            f"Current expenses: {fmt_inr(monthly_exp)}/mo\n"
            f"Expenses at retirement (6% inflation): {fmt_inr(ret['future_monthly_expense'])}/mo\n"
            f"Corpus needed (30yr post-retire, 12% return): {fmt_inr(ret['corpus_needed'])}\n"
            f"Monthly SIP needed: {fmt_inr(ret['monthly_sip_needed'])}"
        ))

        # FIRE analysis
        if income and "ctc" in computed:
            monthly_savings_est = monthly_th - monthly_exp
            fire = fire_calculator(monthly_exp, current_age=current_age,
                                   retirement_age=retire_age, current_savings=0,
                                   monthly_savings=monthly_savings_est)
            add("FIRE ANALYSIS", (
                f"Monthly expenses at retirement (6% inflation): {fmt_inr(fire['monthly_expenses_at_retire'])}/mo\n"
                f"🟢 Lean FIRE (frugal, ×25 of 60%): {fmt_inr(fire['lean_fire_corpus'])}"
                f" — {fire['years_to_lean_fire']} years\n"
                f"🔵 Regular FIRE (4% rule, ×25): {fmt_inr(fire['regular_fire_corpus'])}"
                f" — {fire['years_to_regular_fire']} years\n"
                f"☕ Barista FIRE (70% covered, ×33): {fmt_inr(fire['barista_fire_corpus'])}"
                f" — {fire['years_to_barista_fire']} years\n"
                f"💎 Fat FIRE (luxury, ×50): {fmt_inr(fire['fat_fire_corpus'])}"
                f" — {fire['years_to_fat_fire']} years\n"
                f"🏖️ Coast FIRE (invest once): {fmt_inr(fire['coast_fire_corpus'])}\n"
                f"SIP needed for Regular FIRE: {fmt_inr(fire['sip_needed_for_fire'])}/mo\n"
                f"Recommendation: {fire['fire_recommendation']}"
            ))

    # ═══════════════════ PROPERTY / RENT VS BUY ═══════════════════
    if "property" in topics and "compare" in topics:
        prop_price = None
        rent_amt = None
        for n in sorted(numbers, reverse=True):
            if n >= 1000000 and (not income or n != income):
                prop_price = n
                break
        for n in numbers:
            if 3000 <= n <= 200000:
                rent_amt = n
                break

        if prop_price:
            rent_amt = rent_amt or round(prop_price * 0.003)  # ~0.3% per month
            rvb = rent_vs_buy(prop_price, rent_amt)
            computed.add("rent_vs_buy")
            add("RENT vs BUY ANALYSIS", (
                f"Property: {fmt_inr(prop_price)} | Rent: {fmt_inr(rent_amt)}/mo\n"
                f"BUY: Total cost {fmt_inr(rvb['buy_total_cost'])}, Property value after 20yr: {fmt_inr(rvb['buy_property_value_after'])}\n"
                f"     Net position: {fmt_inr(rvb['buy_net_position'])}\n"
                f"RENT: Total rent {fmt_inr(rvb['rent_total_paid'])}, Investment corpus: {fmt_inr(rvb['rent_investment_corpus'])}\n"
                f"     Net position: {fmt_inr(rvb['rent_net_position'])}\n"
                f"VERDICT: {rvb['recommendation']} wins by {fmt_inr(rvb['advantage_amount'])}\n"
                f"({rvb['key_assumptions']})"
            ))

    # ═══════════════════ FD / PPF ═══════════════════
    if "fd" in topics:
        amt = None
        for n in numbers:
            if n >= 10000 and (not income or n != income):
                amt = n
                break
        if amt:
            fd = fd_calculator(amt, 7.0, 5)
            computed.add("fd")
            add("FD ANALYSIS", (
                f"Principal: {fmt_inr(amt)} @7% for 5yr\n"
                f"Maturity: {fmt_inr(fd['maturity_value'])} | Interest: {fmt_inr(fd['gross_interest'])}\n"
                f"Post-tax return: {fd['effective_post_tax_rate']}% | Real return: {fd['real_return_after_inflation']}%\n"
                f"Verdict: {fd['verdict']}"
            ))

    if "ppf" in topics:
        amt = None
        for n in numbers:
            if 500 <= n <= 150000 and (not income or n != income):
                amt = n
                break
        amt = amt or 150000
        ppf = ppf_calculator(amt)
        computed.add("ppf")
        add("PPF ANALYSIS", (
            f"Annual deposit: {fmt_inr(amt)} (max ₹1.5L) @7.1% for 15yr\n"
            f"Maturity: {fmt_inr(ppf['maturity_value'])} | Interest: {fmt_inr(ppf['total_interest'])}\n"
            f"Tax: {ppf['tax_status']}"
        ))

    # ═══════════════════ RD (RECURRING DEPOSIT) ═══════════════════
    if "rd" in topics:
        from tools.financial_calc import rd_calculator
        amt = None
        for n in numbers:
            if 500 <= n <= 200000 and (not income or n != income):
                amt = n
                break
        amt = amt or 5000
        yrs = 5
        # Look for year/tenure in query context
        yr_m = re.search(r'(\d+)\s*(?:years?|yrs?)\b', query.lower())
        if yr_m:
            yrs = int(yr_m.group(1))
        rd = rd_calculator(amt, 6.5, yrs)
        computed.add("rd")
        add("RD ANALYSIS", (
            f"Monthly deposit: {fmt_inr(amt)} @6.5% for {yrs}yr (quarterly compounding)\n"
            f"Invested: {fmt_inr(rd['total_invested'])} | Maturity: {fmt_inr(rd['maturity_value'])}\n"
            f"Interest: {fmt_inr(rd['total_interest'])} | Yield: {rd['effective_yield_pct']}%"
        ))

    # ═══════════════════ SSY (SUKANYA SAMRIDDHI) ═══════════════════
    if "ssy" in topics:
        from tools.financial_calc import ssy_calculator
        amt = None
        for n in numbers:
            if 250 <= n <= 150000 and (not income or n != income):
                amt = n
                break
        amt = amt or 150000
        girl_age = 5
        for n in numbers:
            if 0 <= n <= 10 and n != amt:
                girl_age = int(n)
                break
        ssy = ssy_calculator(amt, girl_age)
        if "error" not in ssy:
            computed.add("ssy")
            add("SSY ANALYSIS (Sukanya Samriddhi Yojana)", (
                f"Annual deposit: {fmt_inr(amt)} | Girl's age: {girl_age} | Rate: {ssy['interest_rate']}%\n"
                f"Deposit for: {ssy['deposit_years']} years | Matures in: {ssy['maturity_years']} years\n"
                f"Total deposited: {fmt_inr(ssy['total_deposited'])} | Interest: {fmt_inr(ssy['total_interest'])}\n"
                f"Maturity value: {fmt_inr(ssy['maturity_value'])}\n"
                f"Tax: Completely exempt (EEE — deposit, interest, maturity all tax-free)"
            ))

    # ═══════════════════ NPS (NATIONAL PENSION SYSTEM) ═══════════════════
    if "nps" in topics:
        from tools.financial_calc import nps_calculator
        contrib = None
        for n in numbers:
            if 500 <= n <= 200000 and (not income or n != income):
                contrib = n
                break
        contrib = contrib or 5000
        age = 30
        age_m = re.search(r'\b(?:age|am)\s*(\d{2})\b', query.lower())
        if age_m:
            age = int(age_m.group(1))
        elif profile.get("age"):
            age = int(profile["age"])
        nps = nps_calculator(contrib, age)
        if "error" not in nps:
            computed.add("nps")
            add("NPS ANALYSIS", (
                f"Monthly: {fmt_inr(contrib)} | Age: {age} → Retire at 60 ({nps['years_to_retire']}yr)\n"
                f"Invested: {fmt_inr(nps['total_invested'])} | Corpus: {fmt_inr(nps['total_corpus'])}\n"
                f"Lump sum (60%): {fmt_inr(nps['lump_sum_withdrawal'])}\n"
                f"Annuity (40%): {fmt_inr(nps['annuity_investment'])} → ~{fmt_inr(nps['est_monthly_pension'])}/mo pension\n"
                f"Tax: Extra ₹50K deduction under 80CCD(1B) — over and above 80C"
            ))

    # ═══════════════════ NSC (NATIONAL SAVINGS CERTIFICATE) ═══════════════════
    if "nsc" in topics:
        from tools.financial_calc import nsc_calculator
        amt = None
        for n in numbers:
            if n >= 1000 and (not income or n != income):
                amt = n
                break
        amt = amt or 100000
        nsc = nsc_calculator(amt)
        computed.add("nsc")
        add("NSC ANALYSIS", (
            f"Investment: {fmt_inr(amt)} @{nsc['interest_rate']}% for {nsc['tenure_years']}yr (annual compounding)\n"
            f"Maturity: {fmt_inr(nsc['maturity_value'])} | Interest: {fmt_inr(nsc['total_interest'])}\n"
            f"80C benefit: {fmt_inr(nsc['tax_benefit_80c'])} | Lock-in: 5 years"
        ))

    # ═══════════════════ SCSS (SENIOR CITIZENS) ═══════════════════
    if "scss" in topics:
        from tools.financial_calc import scss_calculator
        amt = None
        for n in numbers:
            if n >= 1000 and (not income or n != income):
                amt = n
                break
        amt = amt or 500000
        scss = scss_calculator(amt)
        if "error" not in scss:
            computed.add("scss")
            add("SCSS ANALYSIS (Senior Citizens Savings Scheme)", (
                f"Investment: {fmt_inr(amt)} @{scss['interest_rate']}% for {scss['tenure_years']}yr\n"
                f"Quarterly income: {fmt_inr(scss['quarterly_interest'])} | Annual: {fmt_inr(scss['annual_income'])}\n"
                f"Total interest: {fmt_inr(scss['total_interest'])} | Maturity: {fmt_inr(scss['maturity_value'])}"
            ))

    # ═══════════════════ SWP (SYSTEMATIC WITHDRAWAL) ═══════════════════
    if "swp" in topics:
        from tools.financial_calc import swp_calculator
        corpus = None
        withdrawal = None
        for n in sorted(numbers, reverse=True):
            if n >= 100000 and (not income or n != income):
                corpus = n
                break
        for n in numbers:
            if 1000 <= n <= 200000 and n != corpus and (not income or n != income):
                withdrawal = n
                break
        if corpus:
            withdrawal = withdrawal or round(corpus * 0.02)
            swp = swp_calculator(corpus, withdrawal, 8, 5)
            computed.add("swp")
            status = "⚠️ Corpus EXHAUSTED" if swp.get("corpus_exhausted") else f"Remaining: {fmt_inr(swp['final_value'])}"
            add("SWP ANALYSIS (Systematic Withdrawal Plan)", (
                f"Corpus: {fmt_inr(corpus)} | Withdrawal: {fmt_inr(withdrawal)}/mo @8% for 5yr\n"
                f"Total withdrawn: {fmt_inr(swp['total_withdrawn'])} | {status}"
            ))

    # ═══════════════════ GRATUITY ═══════════════════
    if "gratuity" in topics:
        from tools.financial_calc import gratuity_calculator
        salary = None
        years_svc = None
        for n in numbers:
            if n >= 10000 and (not income or n != income):
                salary = n
                break
        for n in numbers:
            if 5 <= n <= 50 and n != salary:
                years_svc = n
                break
        if salary:
            years_svc = years_svc or 20
            grat = gratuity_calculator(salary, years_svc)
            if "error" not in grat:
                computed.add("gratuity")
                add("GRATUITY CALCULATION", (
                    f"Basic + DA: {fmt_inr(salary)}/mo | Service: {grat['years_of_service']}yr\n"
                    f"Gratuity: {fmt_inr(grat['gratuity_amount'])} (formula: N × B × 15/26)\n"
                    f"Tax exempt: {fmt_inr(grat['tax_exempt_amount'])} | Taxable: {fmt_inr(grat['taxable_amount'])}"
                ))

    # ═══════════════════ EPF ═══════════════════
    if "epf" in topics and "epf" not in computed:
        from tools.financial_calc import epf_calculator
        salary = None
        for n in numbers:
            if n >= 5000 and (not income or n != income):
                salary = n
                break
        if not salary and income:
            salary = round(income * 0.5 / 12)  # basic = 50% of CTC
        salary = salary or 50000
        age = 30
        if profile.get("age"):
            age = int(profile["age"])
        epf = epf_calculator(salary, age)
        if "error" not in epf:
            computed.add("epf")
            add("EPF ANALYSIS", (
                f"Basic: {fmt_inr(salary)}/mo | Age: {age} | Rate: {epf['epf_rate']}%\n"
                f"Your contribution: {fmt_inr(epf['total_employee_contribution'])} | Employer: {fmt_inr(epf['total_employer_contribution'])}\n"
                f"Interest earned: {fmt_inr(epf['total_interest_earned'])}\n"
                f"EPF at 58: {fmt_inr(epf['maturity_value'])}"
            ))

    # ═══════════════════ GST ═══════════════════
    if "gst" in topics:
        from tools.financial_calc import gst_calculator
        amt = None
        for n in numbers:
            if n >= 1:
                amt = n
                break
        if amt:
            rate = 18  # default
            for r in [5, 12, 18, 28]:
                if str(r) in query:
                    rate = r
                    break
            gst = gst_calculator(amt, rate)
            computed.add("gst")
            add("GST CALCULATION", (
                f"Amount: {fmt_inr(amt)} | GST rate: {rate}%\n"
                f"GST: {fmt_inr(gst['gst_amount'])} (CGST: {fmt_inr(gst['cgst'])} + SGST: {fmt_inr(gst['sgst'])})\n"
                f"Total: {fmt_inr(gst['total_amount'])}"
            ))

    # ═══════════════════ CAPITAL GAINS ═══════════════════
    if "capital_gains" in topics:
        buy_price = None
        sell_price = None
        for n in sorted(numbers, reverse=True):
            if n >= 1000:
                if sell_price is None:
                    sell_price = n
                elif buy_price is None:
                    buy_price = n
        if buy_price and sell_price and sell_price > buy_price:
            for asset in ["equity", "debt_mf", "gold", "property", "crypto"]:
                if asset in query.lower() or (asset == "equity" and any(w in query.lower() for w in ["share", "stock"])):
                    cg = capital_gains_tax(buy_price, sell_price, 15, asset)  # Assume 15 months
                    add(f"CAPITAL GAINS ({asset.upper()})", (
                        f"Buy: {fmt_inr(buy_price)} → Sell: {fmt_inr(sell_price)}\n"
                        f"Gain: {fmt_inr(cg['gain'])} | Tax: {fmt_inr(cg['total_tax'])} ({cg['type']})\n"
                        f"Net gain: {fmt_inr(cg['net_gain'])}"
                    ))
                    computed.add("capital_gains")
                    break

    # ═══════════════════ INSURANCE ═══════════════════
    if "insurance" in topics and income:
        dep_m = re.search(r'(\d)\s*dependents?', query.lower())
        deps = int(dep_m.group(1)) if dep_m else (int(profile.get("dependents", 1)))
        ins = insurance_coverage(income, deps)
        computed.add("insurance")
        add("INSURANCE NEEDS", (
            f"Income: {fmt_inr(income)}/yr | Dependents: {deps}\n"
            f"Recommended life cover: {fmt_inr(ins['recommended_life_cover'])} ({ins['multiplier']}× income)\n"
            f"Recommended health cover: {fmt_inr(ins['recommended_health_cover'])}\n"
            f"Approx term premium: {fmt_inr(income * ins['multiplier'] * 0.003)}/yr"
        ))

    # ═══════════════════ EMERGENCY FUND ═══════════════════
    if topics & {"budget", "salary"} and income and "retirement" not in topics:
        if "ctc" in computed:
            monthly_th = ctc_to_take_home(income)["take_home_monthly_new"]
            monthly_exp = round(monthly_th * 0.55)
        else:
            monthly_exp = round(income / 12 * 0.55)
        ef = emergency_fund(monthly_exp, 6)
        computed.add("emergency")
        add("EMERGENCY FUND", f"Monthly expenses ≈ {fmt_inr(monthly_exp)} → Need {fmt_inr(ef['emergency_fund_amount'])} (6 months)")

    # ═══════════════════ EDUCATION LOAN ═══════════════════
    if "education" in topics and "loan" in topics:
        amt = None
        for n in numbers:
            if n >= 100000 and (not income or n != income):
                amt = n
                break
        if amt:
            edu = education_loan_calc(amt, 9.5, 7, 1)
            computed.add("edu_loan")
            add("EDUCATION LOAN", (
                f"Loan: {fmt_inr(amt)} @9.5%, 7yr + 1yr moratorium\n"
                f"EMI: {fmt_inr(edu['emi'])}/mo | Total interest: {fmt_inr(edu['total_interest'])}\n"
                f"80E tax saving: {fmt_inr(edu['estimated_tax_saved_80e'])}\n"
                f"Effective cost after tax: {fmt_inr(edu['effective_cost_after_tax'])}"
            ))

    # ═══════════════════ CROSS-REFERENCE INSIGHTS ═══════════════════
    # Dynamic relationship engine — connects dots between computed analyses
    # like a human expert would, factoring in emotional state and life stage
    insights = []

    # ── Financial relationship insights (based on what was actually computed) ──
    if "ctc" in computed and "loan" in computed:
        data = ctc_to_take_home(income)
        emi_limit = data["take_home_monthly_new"] * 0.40
        insights.append(f"AFFORDABILITY: With take-home {fmt_inr(data['take_home_monthly_new'])}/mo, max safe EMI is {fmt_inr(emi_limit)}/mo (40% rule)")

    if "ctc" in computed and "sip" in computed:
        data = ctc_to_take_home(income)
        ideal_save = data["take_home_monthly_new"] * 0.30
        insights.append(f"SAVINGS TARGET: Aim to save {fmt_inr(ideal_save)}/mo (30% of take-home). EPF already saves {fmt_inr(data['epf_employee'] / 12)}/mo")

    if "retirement" in computed and "sip" in computed:
        insights.append("STRATEGY: Start step-up SIP tied to annual increments — even 10% yearly increase dramatically compounds")

    if "loan" in computed and "sip" in computed and "compare" in topics:
        insights.append(
            "PREPAY vs INVEST: If loan rate < expected investment return (e.g., 8.5% home loan vs 12% equity), "
            "investing typically wins over prepayment for long horizons. But loan prepayment gives GUARANTEED "
            "return (risk-free). Consider: prepay high-rate loans (>10%), invest instead for low-rate loans (<9%)"
        )

    if "rent_vs_buy" in computed and "loan" in computed:
        insights.append(
            "HOME DECISION: These numbers assume discipline to invest the rent savings. "
            "If you won't invest the difference, buying forces savings via EMI. Consider your behaviour, not just math."
        )

    if "insurance" in computed and "ctc" in computed:
        data = ctc_to_take_home(income)
        insights.append(f"PROTECTION GAP: Ensure insurance is in place BEFORE growing wealth. Term plan + health cover are non-negotiable at any income level.")

    if "emergency" in computed and "sip" in computed:
        insights.append("PRIORITY: Build emergency fund FIRST (3-6 months expenses in liquid fund), then start SIP. Never invest emergency money.")

    if "hike" in computed:
        insights.append("LIFESTYLE CREEP: With every hike, increase SIP by at least the hike %. Don't let lifestyle expenses absorb the entire raise.")

    if "tax_opt" in computed and "sip" in computed:
        insights.append("TAX + INVEST: ELSS funds serve double duty — ₹1.5L 80C deduction + equity exposure. Best of both worlds for salaried individuals.")

    # ── Sentiment-aware insights ──
    if sentiment["emotion"] == "anxious":
        if "loan" in computed:
            insights.append("NOTE: Your concern about debt is valid, but structured EMIs are manageable. Focus on building an emergency buffer alongside repayment.")
        elif "retirement" in computed:
            insights.append("NOTE: Starting now, even small SIPs compound significantly. You're asking the right questions — that's already ahead of most people.")
        else:
            insights.append("NOTE: Financial anxiety is normal. A clear plan with small, consistent steps is more effective than trying to solve everything at once.")

    if sentiment["emotion"] == "confused":
        insights.append("SIMPLIFY: Focus on just 2-3 actions. The numbers above show exact ₹ amounts — start with the highest-impact one first.")

    if sentiment["emotion"] == "overwhelmed":
        insights.append("STEP BY STEP: Don't try to do everything at once. Priority order: 1) Emergency fund 2) Insurance 3) Debt management 4) Investments")

    if sentiment["urgency"] == "crisis":
        insights.append("URGENT: In a financial crisis, focus on: 1) Pause non-essential SIPs temporarily 2) Use emergency fund 3) Negotiate with lenders for moratorium 4) Don't liquidate long-term investments at a loss")

    # ── Life stage insights ──
    if sentiment["life_stage"] == "young_professional" and "sip" in computed:
        insights.append("AGE ADVANTAGE: At your age, even ₹5,000/mo in equity SIP for 30yr @12% = ₹1.76 Cr. Time is your biggest asset — start NOW, amount doesn't matter.")

    if sentiment["life_stage"] == "pre_retirement" and "retirement" in computed:
        insights.append("APPROACHING RETIREMENT: Gradually shift from equity to debt (target 40:60 equity:debt by retirement). Lock in guaranteed income streams.")

    if sentiment["risk_comfort"] == "conservative" and "sip" in computed:
        insights.append("RISK NOTE: For conservative investors, consider balanced advantage funds or 60:40 equity:debt allocation. Lower returns but smoother ride.")
    elif sentiment["risk_comfort"] == "aggressive" and "loan" in computed:
        insights.append("RISK NOTE: Even with aggressive returns, paying off high-interest debt (>10%) first is mathematically optimal. It's a risk-free guaranteed return.")

    if insights:
        add("CROSS-REFERENCE INSIGHTS", "\n".join(f"• {i}" for i in insights))

    # ── Sentiment summary for LLM (tells agent HOW to respond) ──
    if sentiment["emotion"] != "neutral" or sentiment["urgency"] != "normal":
        sentiment_hints = []
        if sentiment["emotion"] != "neutral":
            sentiment_hints.append(f"User emotion: {sentiment['emotion']}")
        if sentiment["urgency"] != "normal":
            sentiment_hints.append(f"Urgency: {sentiment['urgency']}")
        if sentiment["risk_comfort"] != "moderate":
            sentiment_hints.append(f"Risk preference: {sentiment['risk_comfort']}")
        if sentiment["life_stage"]:
            sentiment_hints.append(f"Life stage: {sentiment['life_stage']}")
        add("SENTIMENT CONTEXT", " | ".join(sentiment_hints) + "\nAdapt your tone and recommendations accordingly.")

    if not results:
        return ""

    header = f"══ PRE-COMPUTED CALCULATIONS ({len(computed)} analyses) ══"
    footer = "══ END CALCULATIONS — Use these exact numbers in your response ══"
    return f"{header}\n\n" + "\n\n".join(results) + f"\n\n{footer}"
