"""Agent router - LLM-based query classification with agent dependency graph."""
from __future__ import annotations

import json
import logging
import re
import time
from functools import lru_cache
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
        calcs = ", ".join(info["calculators"]) if info["calculators"] else "none"
        lines.append(f"  {agent}: calcs=[{calcs}]")
    return "\n".join(lines)


_COMBINED_PROMPT = """Analyze the query and return a JSON object with THREE fields:
1. "agents": Array of 1-3 agent keys (most relevant first)
2. "search_queries": Array of 0-3 web search strings
3. "complexity": "simple" | "moderate" | "complex"

COMPLEXITY: simple=greetings/calculator/factual lookup (0 searches), moderate=standard advice (1-2 searches), complex=multi-domain/comparison (2-3 searches)

AGENTS:
{agent_list}

AGENT TOOLS:
{agent_graph}

RULES:
- Prefer 1 agent. Use 2-3 only for genuinely multi-domain queries.
- budget_planner handles CTC→take-home internally — don't add tax_advisor for budget queries.
- gold/silver/dollar/FD → general_advisor.

EXAMPLES:
"Hi" → {{"agents":["general_advisor"],"search_queries":[],"complexity":"simple"}}
"EMI for ₹50L at 8.5% 20yr" → {{"agents":["loan_advisor"],"search_queries":[],"complexity":"simple"}}
"Prepay loan or invest?" → {{"agents":["loan_advisor","mutual_fund_advisor"],"search_queries":["home loan prepayment vs SIP India 2026"],"complexity":"complex"}}

Query: "{query}"
"""

# ── Router response cache (avoids re-classifying similar queries) ──
_router_cache = {}  # normalized_query -> (result_dict, timestamp)
_ROUTER_CACHE_TTL = 300  # 5 minutes
_ROUTER_CACHE_MAX = 32


def _normalize_query(q: str) -> str:
    """Normalize query for cache lookup — lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', q.lower())).strip()


def _llm_classify_and_search(query: str, hint_agents: set = None) -> dict:
    """Combined LLM call: classify agents AND generate search queries.

    When hint_agents is provided (from keyword analysis), the LLM prompt
    only includes those candidate agents — shrinking the prompt ~60% and
    cutting classification time ~40-60%. The LLM still makes the nuanced
    final decision, but over a smaller, pre-filtered candidate set.

    Returns dict with:
      - "agents": list of agent keys
      - "search_queries": list of tailored search query strings

    Falls back to empty dict on failure.
    Uses a short-lived cache to avoid repeated LLM calls for similar queries.
    """
    # Check cache first
    cache_key = _normalize_query(query)
    cached = _router_cache.get(cache_key)
    if cached:
        result, ts = cached
        if time.time() - ts < _ROUTER_CACHE_TTL:
            logger.info(f"Router cache hit: {result.get('agents')}")
            return result
        else:
            del _router_cache[cache_key]

    from llm.engine import llm
    llm.initialize()

    # Build agent list — narrowed if we have keyword hints
    if hint_agents and len(hint_agents) >= 2:
        # Use only candidate agents + their graph info (smaller prompt = faster)
        agent_list = "\n".join(
            f"- {key}: {desc}" for key, desc in AGENT_DESCRIPTIONS.items()
            if key in hint_agents
        )
        agent_graph = "\n".join(
            f"  {agent}: calcs=[{', '.join(info['calculators']) if info['calculators'] else 'none'}]"
            for agent, info in AGENT_GRAPH.items()
            if agent in hint_agents
        )
        narrowed = True
        logger.info(f"LLM router narrowed to {len(hint_agents)} candidates: {hint_agents}")
    else:
        # No useful hints — show all agents
        agent_list = "\n".join(
            f"- {key}: {desc}" for key, desc in AGENT_DESCRIPTIONS.items()
        )
        agent_graph = _build_graph_description()
        narrowed = False

    prompt = _COMBINED_PROMPT.format(
        agent_list=agent_list,
        agent_graph=agent_graph,
        query=query,
    )

    try:
        from config import ROUTER_MAX_TOKENS
        # Use fewer tokens when narrowed (less agents to consider)
        max_tokens = min(ROUTER_MAX_TOKENS, 100) if narrowed else ROUTER_MAX_TOKENS

        response = llm.model.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a precise JSON router. Return ONLY a JSON object with 'agents', 'search_queries', and 'complexity' fields. /no_think"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            top_p=0.9,
            max_tokens=max_tokens,
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

        # Store in cache (evict oldest if full)
        if len(_router_cache) >= _ROUTER_CACHE_MAX:
            oldest_key = min(_router_cache, key=lambda k: _router_cache[k][1])
            del _router_cache[oldest_key]
        _router_cache[cache_key] = (result, time.time())

        return result

    except Exception as e:
        logger.error(f"LLM classification failed: {e}")
        return {}


# Keep the old _llm_classify as internal fallback
def _llm_classify(query: str) -> list:
    """Legacy LLM classifier — returns only agent keys (no search queries)."""
    result = _llm_classify_and_search(query)
    return result.get("agents", [])


# ──────────────────────── Keyword Hint Engine ────────────────────────

def _keyword_hints(query: str) -> tuple[set[str], bool]:
    """Extract keyword-based agent candidates from the query.

    Unlike a fast-path, this NEVER makes the final decision (except for
    trivial greetings). It returns a set of candidate agent keys that the
    LLM router can focus on — shrinking its search space from 10 agents
    to 2-4, which cuts classification time ~40-60%.

    Returns:
        (set of candidate agent keys, is_trivial)
        is_trivial=True means greetings/trivial — can skip LLM entirely.
    """
    q = query.lower()

    # ── Greetings / trivial — skip LLM entirely ──
    _greetings = ["hi", "hello", "hey", "thanks", "thank you", "good morning",
                  "good evening", "good afternoon", "bye", "ok", "okay", "sure",
                  "who are you", "what can you do", "help"]
    if any(q.strip() == g or q.strip().startswith(g + " ") or q.strip().startswith(g + ",")
           for g in _greetings):
        return {"general_advisor"}, True

    hits = set()

    # Budget / earning / expense queries
    if any(p in q for p in ["budget", "how much should i earn", "how much do i need to earn",
                             "how much to earn", "cost of living", "decent life",
                             "monthly expense", "expense breakdown", "spending plan",
                             "plan my salary", "salary breakdown", "save money",
                             "50-30-20", "50 30 20", "emergency fund",
                             "ctc", "take home", "take-home", "in-hand", "in hand",
                             "net salary", "monthly salary"]):
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
                             "dividend", "earnings", "nse", "bse", "fii", "dii",
                             "buy.*share", "sell.*share"]):
        hits.add("stock_analyst")

    # Loan queries
    if any(p in q for p in ["home loan", "car loan", "personal loan", "education loan",
                             "loan emi", "cibil", "prepay loan", "loan interest",
                             "emi for", "emi calculator", "calculate emi",
                             "loan eligibility", "repo rate"]):
        hits.add("loan_advisor")

    # Retirement / SIP queries
    if any(p in q for p in ["retire", "retirement", "pension", "corpus plan",
                             "sip", "step up sip", "step-up sip", "ppf", "nps",
                             "epf", "fire number", "lumpsum vs sip", "sip vs lumpsum",
                             "fd", "fixed deposit", "rd", "recurring deposit",
                             "compound interest", "kvp", "scss", "nsc",
                             "how much to invest", "wealth creation", "crore by"]):
        hits.add("retirement_planner")

    # Crypto queries
    if any(p in q for p in ["bitcoin", "ethereum", "crypto", "altcoin", "vda tax"]):
        hits.add("crypto_analyst")

    # Insurance queries
    if any(p in q for p in ["term insurance", "health insurance", "life insurance",
                             "claim settlement", "insurance premium", "mediclaim"]):
        hits.add("insurance_advisor")

    # Mutual fund queries
    if any(p in q for p in ["mutual fund", "elss", "fund nav", "amc",
                             "index fund", "flexi cap", "large cap fund",
                             "mid cap fund", "small cap fund", "direct plan",
                             "regular plan"]):
        hits.add("mutual_fund_advisor")

    # Portfolio queries
    if any(p in q for p in ["portfolio", "asset allocation", "rebalance",
                             "diversif"]):
        hits.add("portfolio_manager")

    # Gold/commodity prices → general
    if any(p in q for p in ["gold price", "silver price", "dollar rate", "fd rate",
                             "rbi policy", "gold rate", "forex rate",
                             "crude oil price", "commodity price"]):
        hits.add("general_advisor")

    # Standalone concept questions (only if no other agent matched)
    if not hits and any(p in q for p in ["what is", "explain", "meaning of",
                                          "define", "how does"]):
        hits.add("general_advisor")

    # Also include dependency agents for richer context (only when few direct hits)
    expanded = set(hits)
    if len(hits) <= 3:
        for agent_key in hits:
            deps = AGENT_GRAPH.get(agent_key, {}).get("depends_on", [])
            for dep in deps[:1]:  # Add top 1 dependency as candidate
                expanded.add(dep)

    # Always include general_advisor as a fallback candidate
    if expanded:
        expanded.add("general_advisor")

    # Cap at 6 candidates — above that it's not narrowing enough to help
    if len(expanded) > 6:
        # Keep direct hits + general, drop dependency expansions
        expanded = hits | {"general_advisor"}

    logger.info(f"Keyword hints: direct={hits}, expanded={expanded}")
    return expanded, False


# ──────────────────────── Main router ────────────────────────

def route_query(query: str, manual_agent: str = None) -> tuple[list, list, str]:
    """Route a query to appropriate agent(s) and generate search queries.

    Hybrid strategy (ROUTER_MODE="hybrid"):
    1. Keywords extract candidate agents (narrows 10 → 2-5)
    2. LLM sees only the candidates + their descriptions (shorter prompt = faster)
    3. LLM makes the nuanced final decision with full context

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

    # Step 1: Keyword hints (instant, <1ms)
    hint_agents = set()
    is_trivial = False
    if ROUTER_MODE in ("hybrid", "keyword_first"):
        hint_agents, is_trivial = _keyword_hints(query)

        # Trivial greetings — skip LLM entirely
        if is_trivial and hint_agents:
            agent_keys = list(hint_agents)
            result = [(key, AGENT_REGISTRY[key]) for key in agent_keys]
            logger.info(f"Trivial fast-path → {agent_keys}")
            return result, [], "simple"

        # keyword_first mode: if only 1 candidate, use it directly (old behavior)
        if ROUTER_MODE == "keyword_first" and len(hint_agents) == 1:
            agent_key = list(hint_agents)[0]
            result = [(agent_key, AGENT_REGISTRY[agent_key])]
            logger.info(f"Keyword-first direct → [{agent_key}]")
            return result, [], "moderate"

    # Step 2: LLM classification (with narrowed candidate list if hints available)
    llm_result = _llm_classify_and_search(query, hint_agents=hint_agents)

    if llm_result.get("agents"):
        agents = llm_result["agents"]
        search_queries = llm_result.get("search_queries", [])
        complexity = llm_result.get("complexity", "moderate")
        result = [(key, AGENT_REGISTRY[key]) for key in agents]
        logger.info(f"LLM routed to: {[r[0] for r in result]}, complexity={complexity}, "
                     f"search_queries={search_queries}, narrowed={bool(hint_agents)}")
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
