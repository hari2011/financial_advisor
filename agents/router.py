"""Agent router - LLM-based query classification with agent dependency graph."""
import json
import logging
import re
from agents.base import BaseAgent
from config import ROUTER_MODE

logger = logging.getLogger("financegpt.router")

from agents.stock_analyst import StockAnalystAgent
from agents.portfolio_manager import PortfolioManagerAgent
from agents.tax_advisor import TaxAdvisorAgent
from agents.retirement_planner import RetirementPlannerAgent
from agents.loan_advisor import LoanAdvisorAgent
from agents.budget_planner import BudgetPlannerAgent
from agents.crypto_analyst import CryptoAnalystAgent
from agents.insurance_advisor import InsuranceAdvisorAgent
from agents.mutual_fund_advisor import MutualFundAdvisorAgent
from agents.general_advisor import GeneralAdvisorAgent

# Instantiate all agents
AGENT_REGISTRY = {
    "stock_analyst": StockAnalystAgent(),
    "portfolio_manager": PortfolioManagerAgent(),
    "tax_advisor": TaxAdvisorAgent(),
    "retirement_planner": RetirementPlannerAgent(),
    "loan_advisor": LoanAdvisorAgent(),
    "budget_planner": BudgetPlannerAgent(),
    "crypto_analyst": CryptoAnalystAgent(),
    "insurance_advisor": InsuranceAdvisorAgent(),
    "mutual_fund_advisor": MutualFundAdvisorAgent(),
    "general_advisor": GeneralAdvisorAgent(),
}

# ──────────────────────── Agent Descriptions ────────────────────────

AGENT_DESCRIPTIONS = {
    "stock_analyst": "Analysing specific STOCKS/SHARES by ticker or company name (Reliance, TCS, HDFC, Apple, Tesla). Company fundamentals (P/E, revenue, earnings). NSE/BSE index analysis (Nifty, Sensex). IPO, FII/DII flows. NOT for gold/silver/forex prices or general market news.",
    "mutual_fund_advisor": "Mutual fund selection, NAV, SIP in mutual funds, ELSS, fund comparison, AMC recommendations (Mirae, Axis, Parag Parikh). Direct vs regular plans. Sectoral/thematic funds.",
    "portfolio_manager": "Asset allocation across multiple asset classes, portfolio diversification, rebalancing, risk-return optimization. SGBs, REITs. NOT for single stock analysis.",
    "tax_advisor": "Income tax calculation, old vs new regime comparison, deductions (80C/80D/80E/24b), capital gains tax (STCG/LTCG), TDS, ITR filing, tax-saving strategies, HRA exemption.",
    "retirement_planner": "Retirement corpus planning, SIP projections/calculations, compound interest, EPF/PPF/NPS, pension, FIRE, step-up SIP, SWP. Long-term wealth building.",
    "loan_advisor": "Home/personal/car/education/gold loans, EMI calculation, interest rate comparison, CIBIL score, prepayment strategy, repo rate impact, loan affordability.",
    "budget_planner": "Monthly budgeting, expense allocation, savings goals, emergency fund, cost management, financial planning for a given income/salary. Uses CTC→take-home internally.",
    "crypto_analyst": "Cryptocurrency prices, Bitcoin, Ethereum, altcoins, crypto tax in India (30% VDA), DeFi, blockchain analysis.",
    "insurance_advisor": "Term life insurance, health insurance, coverage analysis, IRDAI regulations, claim settlement, premium comparison, riders, ULIPs.",
    "general_advisor": "General financial questions, gold/silver/commodity PRICES, forex/dollar rates, RBI policy, economic news, inflation, FD rates, financial concepts, anything that doesn't fit a specialist above.",
}

# ──────────────────────── Agent Dependency Graph ────────────────────────
# Defines how agents relate to each other and what calculators/tools each
# agent can leverage. The LLM uses this graph to:
#   1. Select the RIGHT agents (not just keyword matching)
#   2. Generate RELEVANT search queries based on agent capabilities
#
# Format: agent_key → {depends_on: [], calculators: [], context_needs: []}

AGENT_GRAPH = {
    "budget_planner": {
        "depends_on": ["tax_advisor", "loan_advisor", "insurance_advisor"],
        "calculators": ["ctc_to_take_home", "sip", "emergency_fund"],
        "context_needs": [
            "CTC/salary → take-home calculation (tax deductions, EPF, gratuity)",
            "EMI obligations (home loan, car loan, personal loan)",
            "Insurance premiums (term life, health — non-negotiable before investing)",
            "City-wise cost of living (rent, groceries, school fees, transport)",
            "Savings allocation (SIP, PPF, NPS, emergency fund)",
        ],
    },
    "tax_advisor": {
        "depends_on": ["budget_planner", "loan_advisor"],
        "calculators": ["income_tax", "ctc_to_take_home", "hra_exemption", "capital_gains"],
        "context_needs": [
            "Income slabs and tax regime comparison (old vs new)",
            "Section 80C/80D/24b deduction limits",
            "HRA exemption rules (metro vs non-metro, rent)",
            "Capital gains tax rates (STCG 20%, LTCG 12.5%)",
        ],
    },
    "retirement_planner": {
        "depends_on": ["tax_advisor", "mutual_fund_advisor"],
        "calculators": ["sip", "stepup_sip", "retirement_corpus", "fire", "ppf", "nps", "epf"],
        "context_needs": [
            "Retirement corpus needed (inflation-adjusted)",
            "SIP projections at different return rates",
            "EPF/PPF/NPS contribution and accumulation",
            "FIRE number calculation",
        ],
    },
    "loan_advisor": {
        "depends_on": ["budget_planner", "tax_advisor"],
        "calculators": ["emi", "loan_prepayment", "education_loan"],
        "context_needs": [
            "EMI calculation and affordability (vs income)",
            "Interest rate comparison across banks",
            "Prepayment benefit analysis",
            "Home loan tax benefit under Section 24b",
        ],
    },
    "stock_analyst": {
        "depends_on": ["portfolio_manager", "tax_advisor"],
        "calculators": ["capital_gains", "lumpsum_vs_sip"],
        "context_needs": [
            "Company fundamentals (P/E, revenue, earnings)",
            "NSE/BSE index trends",
            "FII/DII flows and market sentiment",
            "Capital gains tax implications",
        ],
    },
    "portfolio_manager": {
        "depends_on": ["stock_analyst", "mutual_fund_advisor"],
        "calculators": ["sip", "lumpsum", "stepup_sip"],
        "context_needs": [
            "Asset allocation recommendations",
            "Risk-return profiles across asset classes",
            "Diversification strategy",
            "Rebalancing triggers and methods",
        ],
    },
    "mutual_fund_advisor": {
        "depends_on": ["tax_advisor", "retirement_planner"],
        "calculators": ["sip", "mutual_fund_returns", "stepup_sip", "goal_sip"],
        "context_needs": [
            "Fund category comparison (large/mid/small/flexi cap)",
            "ELSS vs other 80C options for tax saving",
            "Direct vs regular plan performance",
            "SIP performance projection",
        ],
    },
    "insurance_advisor": {
        "depends_on": ["retirement_planner", "budget_planner"],
        "calculators": [],
        "context_needs": [
            "Term life coverage (10-15x annual income)",
            "Health insurance family floater adequacy",
            "Premium affordability vs income",
            "Claim settlement ratios",
        ],
    },
    "crypto_analyst": {
        "depends_on": ["tax_advisor"],
        "calculators": ["capital_gains"],
        "context_needs": [
            "Crypto prices and market sentiment",
            "India VDA tax rules (30% flat, 1% TDS)",
            "Portfolio allocation for crypto",
        ],
    },
    "general_advisor": {
        "depends_on": [],
        "calculators": ["compound_interest", "fd", "inflation_goal", "gst"],
        "context_needs": [
            "Gold/silver/commodity prices",
            "Forex rates and RBI policy",
            "FD/RD rates across banks",
            "General economic indicators",
        ],
    },
}

# ──────────────────────── Combined LLM Classifier + Query Generator ────────────────────────

def _build_graph_description() -> str:
    """Format AGENT_GRAPH into a compact string for the LLM prompt."""
    lines = []
    for agent, info in AGENT_GRAPH.items():
        deps = ", ".join(info["depends_on"]) if info["depends_on"] else "none"
        calcs = ", ".join(info["calculators"]) if info["calculators"] else "none"
        needs = "; ".join(info["context_needs"][:3])
        lines.append(f"  {agent}: depends_on=[{deps}] | calcs=[{calcs}] | needs: {needs}")
    return "\n".join(lines)


_COMBINED_PROMPT = """You are a financial query router. Analyze the query and return a JSON object with THREE fields:

1. "agents": Array of 1-3 agent keys (most relevant first)
2. "search_queries": Array of 0-3 web search query strings tailored to find information the selected agents need
3. "complexity": One of "simple", "moderate", or "complex"

COMPLEXITY RULES:
- "simple": Greetings (hi, hello, thanks), single calculator queries (calculate EMI for 50L), direct factual lookups (gold price today), single-concept questions. These need MINIMAL or NO web search.
- "moderate": Standard financial advice queries involving one domain with context needs (tax planning for 15L salary, SIP for retirement). These need web search for current data.
- "complex": Multi-domain queries (prepay loan vs invest?), comparative analysis, comprehensive financial planning, queries with multiple sub-questions. These need thorough research.

SEARCH QUERY RULES based on complexity:
- "simple": 0 search queries (calculator/factual — no web search needed)
- "moderate": 1-2 targeted search queries
- "complex": 2-3 comprehensive search queries

AVAILABLE AGENTS:
{agent_list}

AGENT DEPENDENCY GRAPH (shows inter-relationships, calculators, and context needs):
{agent_graph}

HOW TO USE THE GRAPH:
- Each agent has "depends_on" showing related agents that handle connected topics.
- Each agent has "calculators" it uses internally (you don't need to pick agents for these — the agent handles them).
- Each agent has "context_needs" showing what information it requires to give a good answer.
- Use "context_needs" of the SELECTED agents to generate targeted search queries.
- Do NOT add dependent agents unless the user's query explicitly covers their domain too.
- budget_planner handles CTC→take-home internally via its calculators — do NOT add tax_advisor for simple budget queries.

ROUTING RULES:
- PREFER FEWER agents (1 is ideal, 2-3 only for genuinely multi-domain queries).
- "how much should I earn" / "cost of living" / "plan my budget" → ["budget_planner"] ONLY.
- tax calculation / regime comparison → ["tax_advisor"] ONLY.
- SIP / retirement / corpus → ["retirement_planner"] ONLY.
- loan EMI / prepayment → ["loan_advisor"] ONLY.
- stock analysis → ["stock_analyst"], add "portfolio_manager" only if allocation advice needed.
- gold/silver/dollar price → ["general_advisor"].
- Multi-domain: "should I prepay loan OR invest?" → ["loan_advisor", "portfolio_manager"].

SEARCH QUERY RULES:
- Generate 0-3 concise, specific search queries based on complexity (see above).
- Tailor queries to what the SELECTED agents need (see "context_needs").
- Include India-specific terms, city names, time period (2025/2026) where relevant.
- Do NOT generate duplicate or overlapping queries.
- Make queries factual and searchable (not questions, not conversational).

EXAMPLES:
Query: "Hi, how are you?"
→ {{"agents": ["general_advisor"], "search_queries": [], "complexity": "simple"}}

Query: "Calculate EMI for ₹50 lakh home loan at 8.5% for 20 years"
→ {{"agents": ["loan_advisor"], "search_queries": [], "complexity": "simple"}}

Query: "I want to live a decent life in Chennai with family of 5, how much should I earn?"
→ {{"agents": ["budget_planner"], "search_queries": ["Chennai cost of living family of 5 monthly expenses 2026", "Chennai rent school fees groceries transport expenses India"], "complexity": "moderate"}}

Query: "Should I prepay my home loan or invest in mutual funds?"
→ {{"agents": ["loan_advisor", "mutual_fund_advisor"], "search_queries": ["home loan prepayment vs mutual fund SIP comparison India 2026", "current home loan interest rates India 2026"], "complexity": "complex"}}

Query: "What's the gold price today?"
→ {{"agents": ["general_advisor"], "search_queries": ["gold price India today per gram 24 carat"], "complexity": "simple"}}

Return ONLY valid JSON, no other text.

Query: "{query}"
"""


def _llm_classify_and_search(query: str) -> dict:
    """Combined LLM call: classify agents AND generate search queries.

    Returns dict with:
      - "agents": list of agent keys
      - "search_queries": list of tailored search query strings

    Falls back to empty dict on failure.
    """
    from llm.engine import llm
    llm.initialize()

    agent_list = "\n".join(
        f"- {key}: {desc}" for key, desc in AGENT_DESCRIPTIONS.items()
    )
    agent_graph = _build_graph_description()
    prompt = _COMBINED_PROMPT.format(
        agent_list=agent_list,
        agent_graph=agent_graph,
        query=query,
    )

    try:
        response = llm.model.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a precise JSON router. Return ONLY a JSON object with 'agents', 'search_queries', and 'complexity' fields. /no_think"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            top_p=0.9,
            max_tokens=300,
            repeat_penalty=1.0,
        )
        raw = response["choices"][0]["message"]["content"].strip()
        raw = re.sub(r'<think>.*?</think>\s*', '', raw, flags=re.DOTALL).strip()
        if '<think>' in raw:
            raw = raw[:raw.index('<think>')].strip()
        logger.info(f"LLM router raw output: {raw}")

        # Parse JSON object
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
        else:
            logger.warning(f"LLM router returned non-JSON: {raw}")
            return {}

        # Validate agents
        agents = parsed.get("agents", [])
        valid_agents = [a for a in agents if a in AGENT_REGISTRY][:3]
        if not valid_agents:
            logger.warning(f"LLM router returned unknown agents: {agents}")
            return {}

        # Validate search queries
        search_queries = parsed.get("search_queries", [])
        valid_queries = [q.strip() for q in search_queries
                        if isinstance(q, str) and len(q.strip()) > 5][:3]

        # Validate complexity
        complexity = parsed.get("complexity", "moderate")
        if complexity not in ("simple", "moderate", "complex"):
            complexity = "moderate"

        result = {
            "agents": valid_agents,
            "search_queries": valid_queries,
            "complexity": complexity,
        }
        logger.info(f"LLM classified → agents={valid_agents}, complexity={complexity}, queries={len(valid_queries)}")
        return result

    except Exception as e:
        logger.error(f"LLM classification failed: {e}")
        return {}


# Keep the old _llm_classify as internal fallback
def _llm_classify(query: str) -> list:
    """Legacy LLM classifier — returns only agent keys (no search queries)."""
    result = _llm_classify_and_search(query)
    return result.get("agents", [])


# ──────────────────────── Keyword fast-path ────────────────────────

def _keyword_fast_path(query: str) -> list[str] | None:
    """Fast keyword classification for clearly single-domain queries.

    Returns list of agent keys if the query unambiguously matches ONE domain.
    Returns None to fall through to LLM classification for ambiguous queries.
    Saves ~5s by avoiding an LLM inference call on obvious queries.
    """
    q = query.lower()

    hits = set()

    # Budget / earning / expense queries
    if any(p in q for p in ["budget", "how much should i earn", "how much do i need to earn",
                             "how much to earn", "cost of living", "decent life",
                             "monthly expense", "expense breakdown", "spending plan"]):
        hits.add("budget_planner")

    # Tax queries
    if any(p in q for p in ["income tax", "pay tax", "save tax", "tax on", "tax for",
                             "tax slab", "tax rate", "how much tax", "what tax",
                             "calculate tax", "tax planning", "my tax",
                             "80c", "80d", "itr filing", "tax regime",
                             "old regime", "new regime", "capital gain", "tax saving",
                             "tax deduction", "hra exemption"]):
        hits.add("tax_advisor")

    # Stock queries
    if any(p in q for p in ["stock", "share price", "nifty", "sensex", "ipo",
                             "dividend", "earnings"]):
        hits.add("stock_analyst")

    # Loan queries
    if any(p in q for p in ["home loan", "car loan", "personal loan", "education loan",
                             "loan emi", "cibil", "prepay loan", "loan interest"]):
        hits.add("loan_advisor")

    # Retirement queries
    if any(p in q for p in ["retire", "retirement", "pension", "corpus plan"]):
        hits.add("retirement_planner")

    # Crypto queries
    if any(p in q for p in ["bitcoin", "ethereum", "crypto", "altcoin"]):
        hits.add("crypto_analyst")

    # Insurance queries
    if any(p in q for p in ["term insurance", "health insurance", "life insurance",
                             "claim settlement"]):
        hits.add("insurance_advisor")

    # Mutual fund queries
    if any(p in q for p in ["mutual fund", "elss", "fund nav", "amc"]):
        hits.add("mutual_fund_advisor")

    # Portfolio queries
    if any(p in q for p in ["portfolio", "asset allocation", "rebalance"]):
        hits.add("portfolio_manager")

    # Gold/commodity prices → general
    if any(p in q for p in ["gold price", "silver price", "dollar rate", "fd rate",
                             "rbi policy"]):
        hits.add("general_advisor")

    # Only fast-path when exactly ONE domain matches (unambiguous)
    if len(hits) == 1:
        agent_key = hits.pop()
        logger.info(f"Keyword fast-path → [{agent_key}]")
        return [agent_key]

    if len(hits) > 1:
        logger.info(f"Keyword fast-path: multi-domain ({hits}), deferring to LLM")

    return None  # Ambiguous or no clear signal — use LLM


# ──────────────────────── Main router ────────────────────────

def route_query(query: str, manual_agent: str = None) -> tuple[list, list, str]:
    """Route a query to appropriate agent(s) and generate search queries.

    Returns:
        tuple of (
            list of (agent_key, agent_instance) tuples,
            list of search query strings for deep_research,
            complexity level: "simple", "moderate", or "complex"
        )
    """
    # Manual selection overrides everything
    if manual_agent and manual_agent in AGENT_REGISTRY:
        logger.info(f"Manual agent selection: {manual_agent}")
        return [(manual_agent, AGENT_REGISTRY[manual_agent])], [], "moderate"

    # Keyword fast-path: enabled when ROUTER_MODE="keyword_first"
    # LLM classification is always the fallback regardless of mode
    if ROUTER_MODE == "keyword_first":
        fast = _keyword_fast_path(query)
        if fast:
            result = [(key, AGENT_REGISTRY[key]) for key in fast]
            logger.info(f"Fast-path routed to: {[r[0] for r in result]}")
            return result, [], "moderate"  # Keyword path defaults to moderate

    else:
        logger.info(f"Router mode: {ROUTER_MODE} — skipping keyword fast-path")

    # Combined LLM classification + search query generation
    llm_result = _llm_classify_and_search(query)

    if llm_result.get("agents"):
        agents = llm_result["agents"]
        search_queries = llm_result.get("search_queries", [])
        complexity = llm_result.get("complexity", "moderate")
        result = [(key, AGENT_REGISTRY[key]) for key in agents]
        logger.info(f"LLM routed to: {[r[0] for r in result]}, complexity={complexity}, search_queries={search_queries}")
        return result, search_queries, complexity

    # Fallback — general_advisor
    logger.info("LLM classification failed — defaulting to general_advisor")
    return [("general_advisor", AGENT_REGISTRY["general_advisor"])], [], "moderate"


def get_agent(agent_key: str) -> BaseAgent:
    """Get a specific agent by key."""
    return AGENT_REGISTRY.get(agent_key, AGENT_REGISTRY["general_advisor"])


def list_agents() -> dict:
    """List all available agents with descriptions."""
    return {
        key: {"name": agent.name, "icon": agent.icon, "description": agent.description}
        for key, agent in AGENT_REGISTRY.items()
    }
