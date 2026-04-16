"""Agent router - LLM-based query classification to the right agent(s)."""
import json
import logging
from agents.base import BaseAgent

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
- tax_advisor + retirement_planner + budget_planner: CTC/salary queries need tax (take-home), retirement (SIP capacity), budget (allocation)
- tax_advisor + mutual_fund_advisor: ELSS vs other 80C options, tax-saving funds
- tax_advisor + loan_advisor: Home loan 24b deduction, loan vs invest decisions
- loan_advisor + portfolio_manager: "Should I prepay loan or invest?" needs both
- retirement_planner + mutual_fund_advisor: SIP in specific funds for retirement
- portfolio_manager + stock_analyst + mutual_fund_advisor: "Build a portfolio" needs all three
- insurance_advisor + retirement_planner: Term insurance coverage linked to retirement corpus
- budget_planner + loan_advisor: EMI affordability depends on budget

RULES:
- Return a JSON array of 1-3 agent key strings, most relevant first.
- Simple price checks (gold, silver, dollar, crude oil) → ["general_advisor"]
- Specific stock/company analysis (Reliance, TCS, Nifty trend) → ["stock_analyst"]
- Stock investing advice (best stocks, dividend, value, long-term) → ["stock_analyst", "portfolio_manager"]
- Tax calculation or regime comparison → ["tax_advisor"]
- SIP/retirement/corpus planning → ["retirement_planner"]
- Loan EMI or affordability → ["loan_advisor"]
- Budget or expense allocation → ["budget_planner"]
- Use the relationship graph above to add complementary agents for multi-domain queries.
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


# ──────────────────────── Main router ────────────────────────

def route_query(query: str, manual_agent: str = None) -> list:
    """Route a query to one or more appropriate agents using LLM classification.
    Returns list of (agent_key, agent_instance) tuples.
    """
    # Manual selection overrides everything
    if manual_agent and manual_agent in AGENT_REGISTRY:
        logger.info(f"Manual agent selection: {manual_agent}")
        return [(manual_agent, AGENT_REGISTRY[manual_agent])]

    # LLM-based classification
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
