"""Agent router - LLM-based query classification to the right agent(s)."""
import json
import logging
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

# Agent descriptions — precise scope boundaries so the LLM picks correctly
AGENT_DESCRIPTIONS = {
    "stock_analyst": "Analysing specific STOCKS/SHARES by ticker or company name (Reliance, TCS, HDFC, Apple, Tesla). Company fundamentals (P/E, revenue, earnings). NSE/BSE index analysis (Nifty, Sensex). IPO, FII/DII flows. NOT for gold/silver/forex prices or general market news.",
    "mutual_fund_advisor": "Mutual fund selection, NAV, SIP in mutual funds, ELSS, fund comparison, AMC recommendations (Mirae, Axis, Parag Parikh). Direct vs regular plans. Sectoral/thematic funds.",
    "portfolio_manager": "Asset allocation across multiple asset classes, portfolio diversification, rebalancing, risk-return optimization. SGBs, REITs. NOT for single stock analysis.",
    "tax_advisor": "Income tax calculation, old vs new regime comparison, deductions (80C/80D/80E/24b), capital gains tax (STCG/LTCG), TDS, ITR filing, tax-saving strategies, HRA exemption.",
    "retirement_planner": "Retirement corpus planning, SIP projections/calculations, compound interest, EPF/PPF/NPS, pension, FIRE, step-up SIP, SWP. Long-term wealth building.",
    "loan_advisor": "Home/personal/car/education/gold loans, EMI calculation, interest rate comparison, CIBIL score, prepayment strategy, repo rate impact, loan affordability.",
    "budget_planner": "Monthly budgeting, expense allocation, savings goals, emergency fund, cost management, financial planning for a given income/salary.",
    "crypto_analyst": "Cryptocurrency prices, Bitcoin, Ethereum, altcoins, crypto tax in India (30% VDA), DeFi, blockchain analysis.",
    "insurance_advisor": "Term life insurance, health insurance, coverage analysis, IRDAI regulations, claim settlement, premium comparison, riders, ULIPs.",
    "general_advisor": "General financial questions, gold/silver/commodity PRICES, forex/dollar rates, RBI policy, economic news, inflation, FD rates, financial concepts, anything that doesn't fit a specialist above.",
}

# ──────────────────────── LLM-based classifier ────────────────────────

_CLASSIFIER_PROMPT = """Classify this financial query into the BEST agent(s) from the list below.

Agents:
{agent_list}

AGENT RELATIONSHIP GRAPH — use this to pick complementary agents:
- stock_analyst + portfolio_manager: Stock picks need allocation context (dividend stocks, long-term investing, portfolio building)
- stock_analyst + tax_advisor: Capital gains (STCG/LTCG), tax harvesting on stocks
- tax_advisor + budget_planner: CTC/salary breakdown queries that EXPLICITLY ask about BOTH tax computation AND budget allocation
- tax_advisor + mutual_fund_advisor: ELSS vs other 80C options, tax-saving funds
- tax_advisor + loan_advisor: Home loan 24b deduction, loan vs invest decisions
- loan_advisor + portfolio_manager: "Should I prepay loan or invest?" needs both
- retirement_planner + mutual_fund_advisor: SIP in specific funds for retirement
- retirement_planner + budget_planner: Long-term planning asking about BOTH retirement corpus AND current budget
- portfolio_manager + stock_analyst + mutual_fund_advisor: "Build a portfolio" needs all three
- insurance_advisor + retirement_planner: Term insurance coverage linked to retirement corpus
- budget_planner + loan_advisor: EMI affordability depends on budget

RULES:
- Return a JSON array of 1-3 agent key strings, most relevant first.
- PREFER FEWER agents. Use 1 agent for simple queries, 2-3 ONLY when the query genuinely spans multiple domains.
- Pure budget/expense/earning queries ("how much should I earn", "plan my budget", "cost of living") → ["budget_planner"] ONLY. Budget planner handles CTC→take-home internally.
- Simple price checks (gold, silver, dollar, crude oil) → ["general_advisor"]
- Specific stock/company analysis (Reliance, TCS, Nifty trend) → ["stock_analyst"]
- Stock investing advice (best stocks, dividend, value, long-term) → ["stock_analyst", "portfolio_manager"]
- Tax calculation or regime comparison → ["tax_advisor"]
- SIP/retirement/corpus planning → ["retirement_planner"]
- Loan EMI or affordability → ["loan_advisor"]
- Budget or expense allocation → ["budget_planner"]
- Use the relationship graph above ONLY when the query explicitly mentions topics from multiple domains.
- Return ONLY valid JSON, no other text.

Query: "{query}"
"""


def _llm_classify(query: str) -> list:
    """Use LLM to classify query into one or more agent keys."""
    from llm.engine import llm
    llm.initialize()

    agent_list = "\n".join(
        f"- {key}: {desc}" for key, desc in AGENT_DESCRIPTIONS.items()
    )
    prompt = _CLASSIFIER_PROMPT.format(agent_list=agent_list, query=query)

    try:
        response = llm.model.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a precise JSON classifier. Return ONLY a JSON array of agent keys. /no_think"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            top_p=0.9,
            max_tokens=150,
            repeat_penalty=1.0,
        )
        raw = response["choices"][0]["message"]["content"].strip()
        # Strip any <think>...</think> blocks Qwen3 may emit despite /no_think
        import re
        raw = re.sub(r'<think>.*?</think>\s*', '', raw, flags=re.DOTALL).strip()
        # Handle unclosed <think> block (model hit max_tokens mid-think)
        if '<think>' in raw:
            raw = raw[:raw.index('<think>')].strip()
        logger.info(f"LLM classifier raw output: {raw}")

        # Parse JSON array
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            agents = json.loads(raw[start:end])
        else:
            logger.warning(f"LLM classifier returned non-JSON: {raw}")
            return []

        # Validate agent keys
        valid = [a for a in agents if a in AGENT_REGISTRY]
        if not valid:
            logger.warning(f"LLM classifier returned unknown agents: {agents}")
            return []

        logger.info(f"LLM classified → {valid}")
        return valid[:3]

    except Exception as e:
        logger.error(f"LLM classification failed: {e}")
        return []


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

def route_query(query: str, manual_agent: str = None) -> list:
    """Route a query to one or more appropriate agents using LLM classification.
    Returns list of (agent_key, agent_instance) tuples.
    """
    # Manual selection overrides everything
    if manual_agent and manual_agent in AGENT_REGISTRY:
        logger.info(f"Manual agent selection: {manual_agent}")
        return [(manual_agent, AGENT_REGISTRY[manual_agent])]

    # Keyword fast-path: enabled when ROUTER_MODE="keyword_first"
    # LLM classification is always the fallback regardless of mode
    if ROUTER_MODE == "keyword_first":
        fast = _keyword_fast_path(query)
        if fast:
            result = [(key, AGENT_REGISTRY[key]) for key in fast]
            logger.info(f"Fast-path routed to: {[r[0] for r in result]}")
            return result
    else:
        logger.info(f"Router mode: {ROUTER_MODE} — skipping keyword fast-path")

    # LLM-based classification (always used as fallback, or primary when mode=llm_only)
    llm_agents = _llm_classify(query)

    if llm_agents:
        result = [(key, AGENT_REGISTRY[key]) for key in llm_agents]
        logger.info(f"LLM routed to: {[r[0] for r in result]}")
        return result

    # Fallback — general_advisor
    logger.info("LLM classification failed — defaulting to general_advisor")
    return [("general_advisor", AGENT_REGISTRY["general_advisor"])]


def get_agent(agent_key: str) -> BaseAgent:
    """Get a specific agent by key."""
    return AGENT_REGISTRY.get(agent_key, AGENT_REGISTRY["general_advisor"])


def list_agents() -> dict:
    """List all available agents with descriptions."""
    return {
        key: {"name": agent.name, "icon": agent.icon, "description": agent.description}
        for key, agent in AGENT_REGISTRY.items()
    }
