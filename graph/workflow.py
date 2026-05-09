"""
LangGraph workflow for FinanceGPT.
Replaces the manual orchestration in server.py with a declarative graph.

Graph flow:
  route → gather_context (parallel per agent) → build_prompt → stream_llm

State carries everything: query, routed agents, context, profile, response tokens.
"""
from __future__ import annotations

import re
import time
import json
import logging
import asyncio
from typing import Annotated, Any
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agents.router import route_query, AGENT_REGISTRY
from config import AGENTS, AGENT_ICONS, LLM_CONFIG

logger = logging.getLogger("financegpt.graph")


# ──────────────────────── State ────────────────────────

class GraphState(dict):
    """TypedDict-like state for the graph. Using dict subclass for flexibility."""
    pass


# Fact extraction patterns (moved from server.py ChatHistoryManager)
_NUM_RE = re.compile(
    r'₹[\d,\.]+\s*(?:lakhs?|lacs?|crores?|cr|L|K)?'
    r'|[\d,\.]+\s*(?:lakhs?|lacs?|crores?|cr)\b'
    r'|\b\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\s*%',
    re.IGNORECASE,
)
_FACT_KEYWORDS = re.compile(
    r'\b(?:salary|income|ctc|take[- ]?home|emi|sip|rent|expenses?|loan|insurance|'
    r'portfolio|investments?|mutual fund|fd|ppf|nps|epf|'
    r'age|retire|dependents?|goal|risk|debt|savings?|budget|premium)\b',
    re.IGNORECASE,
)


def _categorize_fact(line: str) -> str | None:
    """Return a profile key based on the dominant financial keyword."""
    ll = line.lower()

    def has_word(word):
        return bool(re.search(rf'\b{word}\b', ll))

    if has_word('take-home') or 'take home' in ll:
        return "take_home"
    if has_word('ctc'):
        return "income"
    if has_word('salary') or has_word('income'):
        return "income"
    if has_word('emi'):
        return "emi"
    if has_word('rent'):
        return "rent"
    if has_word('sip'):
        return "sip"
    if has_word('loan'):
        return "loan"
    if any(has_word(w) for w in ['insurance', 'premium', 'life cover', 'health cover', 'term cover']):
        return "insurance"
    if any(has_word(w) for w in ['retire', 'corpus']):
        return "retirement"
    if has_word('saving') or has_word('savings'):
        return "savings"
    if any(has_word(w) for w in ['expenses?', 'spend', 'budget']):
        return "expenses"
    if any(has_word(w) for w in ['portfolio', 'investments?', 'mutual fund', 'ppf', 'nps']):
        return "investments"
    if any(has_word(w) for w in ['goal', 'target']):
        return "goal"
    return None


def extract_profile_facts(text: str, existing_profile: dict) -> dict:
    """Extract financial facts from text and merge into profile."""
    profile = dict(existing_profile)
    segments = re.split(r'\n|\.\s+', text)

    for seg in segments:
        seg = seg.strip()
        if not seg or len(seg) < 5:
            continue
        has_keyword = bool(_FACT_KEYWORDS.search(seg))
        numbers = _NUM_RE.findall(seg)
        if has_keyword and numbers:
            key = _categorize_fact(seg)
            if key and key not in profile:
                profile[key] = seg[:100].strip()

    tl = text.lower()
    age_m = re.search(r'\b(?:i am|i.m|age\s*(?:is)?)\s*(\d{2})\b', tl)
    if not age_m:
        age_m = re.search(r'\b(\d{2})\s*(?:years?\s*old|yrs?\s*old)\b', tl)
    if age_m and "age" not in profile:
        profile["age"] = age_m.group(1)
    risk_m = re.search(r'\b(aggressive|moderate|conservative)\b', tl)
    if risk_m and "risk_appetite" not in profile:
        profile["risk_appetite"] = risk_m.group(1).capitalize()
    dep_m = re.search(r'(\d)\s*dependents?', tl)
    if dep_m and "dependents" not in profile:
        profile["dependents"] = dep_m.group(1)

    return profile


def format_profile(profile: dict) -> str:
    """Format profile dict into compact string for LLM."""
    if not profile:
        return ""
    key_labels = {
        "age": "Age", "income": "Income/CTC", "take_home": "Take-home",
        "expenses": "Expenses", "rent": "Rent", "emi": "EMI", "sip": "SIP",
        "loan": "Loan", "insurance": "Insurance", "savings": "Savings",
        "investments": "Investments", "retirement": "Retirement", "goal": "Goal",
        "risk_appetite": "Risk Appetite", "dependents": "Dependents",
    }
    lines = []
    for key, label in key_labels.items():
        if key in profile:
            lines.append(f"- {label}: {profile[key]}")
    for key, value in profile.items():
        if key not in key_labels:
            lines.append(f"- {key}: {value}")
    result = "\n".join(lines)
    return result[:500] if len(result) > 500 else result


# ──────────────────────── Node Functions ────────────────────────

def route_node(state: dict) -> dict:
    """Route query to appropriate agent(s) using keyword + LLM hybrid router.
    
    Also determines query complexity (simple/moderate/complex) which controls:
    - Whether context gathering runs (simple queries skip it)
    - Whether response reflection runs (complex queries get quality checks)
    - Which tools are invoked (adaptive tool selection)
    """
    query = state["query"]
    manual = state.get("manual_agent")

    manual_key = None if manual == "auto" else manual
    routed, search_queries, complexity = route_query(query, manual_key)

    agent_keys = [r[0] for r in routed]
    agent_instances = {r[0]: r[1] for r in routed}

    # Build agent info for frontend
    agent_info = []
    for rk, ra in routed:
        agent_info.append({
            "key": rk,
            "name": AGENTS.get(rk, "General Advisor"),
            "icon": AGENT_ICONS.get(rk, "🤖"),
        })

    logger.info(f"Routed to: {agent_keys} | complexity: {complexity}")
    if search_queries:
        logger.info(f"LLM search queries: {search_queries}")
    return {
        "agent_keys": agent_keys,
        "agent_instances": agent_instances,
        "agent_info": agent_info,
        "search_queries": search_queries,
        "complexity": complexity,
    }


def gather_context_node(state: dict) -> dict:
    """Gather context from all routed agents (parallel where safe).
    
    Adaptive tool selection based on query complexity:
    - simple: Skip deep research + web search, run only calculators + agent context
    - moderate: Run all tools normally
    - complex: Run all tools with higher search limits
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    query = state["query"]
    agent_keys = state["agent_keys"]
    agent_instances = state["agent_instances"]
    session_files = state.get("session_files", [])
    profile = state.get("profile", {})
    complexity = state.get("complexity", "moderate")

    t0 = time.time()
    all_contexts = []

    # ── Inject pre-cached market briefing (instant, no network call) ──
    # Always inject for market-related queries; skip only for greetings/pure math
    _market_kw = ["gold", "silver", "nifty", "sensex", "market", "stock", "share",
                  "dollar", "forex", "crude", "oil", "rate", "price", "fd", "ppf",
                  "epf", "today", "current", "latest", "live", "sona", "chandi"]
    _is_market_query = any(w in query.lower() for w in _market_kw)
    if complexity != "simple" or _is_market_query:
        from tools.market_prefetch import get_market_briefing
        prefetch_briefing = get_market_briefing()
        if prefetch_briefing:
            all_contexts.append(prefetch_briefing)
            logger.info(f"Pre-cached market briefing: {len(prefetch_briefing)} chars")

    # ── Launch independent I/O tasks in parallel ──
    # smart_calc is CPU-only (~50ms), the rest are I/O-bound.
    # LLM calls are NOT made here, so thread-safety is fine.

    subtimings = {}  # tag -> seconds

    def _timed(tag, fn):
        """Run fn, record its wall-clock time under tag, return result."""
        _t = time.time()
        result = fn()
        subtimings[tag] = round(time.time() - _t, 2)
        return result

    def _smart_calc():
        from tools.smart_calc import smart_calculate
        return _timed("smart_calc", lambda: smart_calculate(query, profile))

    def _deep_research():
        from tools.deep_research import deep_research
        from config import DEEP_RESEARCH_MAX_CHARS
        sq = state.get("search_queries")  # LLM-generated queries from router
        max_chars = DEEP_RESEARCH_MAX_CHARS if complexity != "complex" else min(DEEP_RESEARCH_MAX_CHARS + 2000, 7000)
        return _timed("deep_research", lambda: deep_research(
            query, max_context_chars=max_chars, search_queries=sq or None))

    def _agent_context(rk):
        ra = agent_instances[rk]
        def _inner():
            ctx = ra.gather_context(query)
            if ctx and ctx.strip():
                label = AGENTS.get(rk, rk)
                return f"--- {label} ---\n{ctx}"
            return None
        return _timed(f"agent:{rk}", _inner)

    with ThreadPoolExecutor(max_workers=6, thread_name_prefix="gather") as pool:
        futures = {}
        # Use pre-computed smart_calc if available (overlapped with routing)
        precalc = state.get("_precalc_result")
        if precalc:
            all_contexts.append(precalc)
            logger.info(f"Using pre-computed smart_calc: {len(precalc)} chars")
        else:
            futures[pool.submit(_smart_calc)] = "smart_calc"
        # Skip deep research for simple queries (greetings, pure calculations)
        if complexity != "simple":
            futures[pool.submit(_deep_research)] = "deep_research"
        else:
            logger.info("Simple query — skipping deep research + web search")
        for rk in agent_keys:
            futures[pool.submit(_agent_context, rk)] = f"agent:{rk}"

        deep_research_result = None
        for future in as_completed(futures):
            tag = futures[future]
            try:
                result = future.result()
                if result:
                    if tag == "deep_research":
                        deep_research_result = result
                        logger.info(f"[{subtimings.get('deep_research','?')}s] Deep research: {len(result)} chars")
                    elif tag == "smart_calc":
                        all_contexts.append(result)
                        logger.info(f"[{subtimings.get('smart_calc','?')}s] Smart calc: {len(result)} chars")
                    else:
                        all_contexts.append(result)
                        logger.info(f"[{subtimings.get(tag,'?')}s] {tag}: {len(result)} chars")
                else:
                    logger.info(f"[{subtimings.get(tag, '?')}s] {tag}: no data")
            except Exception as e:
                logger.warning(f"{tag} failed: {e}")

        # Deep research fallback to shallow search (skip for simple queries)
        if deep_research_result:
            all_contexts.append(deep_research_result)
        elif complexity != "simple":
            try:
                from tools.web_search import query_web_context
                web_ctx = query_web_context(query)
                if web_ctx:
                    all_contexts.append(web_ctx)
            except Exception as e2:
                logger.warning(f"Fallback web context also failed: {e2}")

    context = "\n\n".join(all_contexts)

    # Inject uploaded file content
    if session_files:
        file_parts = []
        for fdata in session_files:
            if fdata.get("content"):
                file_parts.append(
                    f"--- UPLOADED FILE: {fdata['filename']} ({fdata['type']}) ---\n"
                    f"{fdata['content']}"
                )
        if file_parts:
            context = "\n\n".join(file_parts) + "\n\n" + context
            logger.info(f"Injected {len(session_files)} uploaded file(s)")

    ctx_time = time.time() - t0
    logger.info(f"Total context: {len(context)} chars in {ctx_time:.1f}s | subtimings={subtimings}")
    return {
        "context": context,
        "context_time": ctx_time,
        "context_subtimings": subtimings,
    }


def build_prompt_node(state: dict) -> dict:
    """Build system prompt and apply token budget trimming."""
    agent_keys = state["agent_keys"]
    agent_instances = state["agent_instances"]
    context = state["context"]
    query = state["query"]
    profile = state.get("profile", {})

    # Current date and knowledge awareness prefix
    from datetime import date
    today = date.today().strftime("%d %B %Y")
    awareness = (
        f"Date: {today}. Use [CONTEXT DATA] for current facts — do NOT guess. "
        "Use PRE-COMPUTED ₹ amounts directly — do NOT re-calculate. "
        "Cite web sources as [1],[2] inline. Sources list at end.\n"
        "REASONING: Before answering, mentally identify: (1) What exactly the user needs, "
        "(2) Which data/calculations to use, (3) Key assumptions to state. "
        "Provide concrete ₹ numbers, not vague ranges. Show your work for calculations.\n"
        "OUTPUT STYLE: The user may not be a financial expert. Explain key concepts clearly "
        "so they understand WHY, not just WHAT. Use bullet points and tables for data. "
        "₹ in Lakhs/Crores. Stay focused on the core question — no generic greetings, "
        "no motivational filler, no repeating the question back. End with clear actionable next steps.\n"
        "MISSING INFORMATION: If the user's query requires specific financial details that are NOT "
        "provided and NOT available in the context/profile (e.g., income, age, city, rent, existing "
        "investments, family size, loan details), DO NOT silently assume values. Instead:\n"
        "1. Point out what information is missing and why it matters for accurate advice.\n"
        "2. Provide a PRELIMINARY answer using clearly labeled assumptions (e.g., 'Assuming metro city, "
        "₹25K rent, no existing 80C investments...').\n"
        "3. End with specific questions asking the user to provide the missing details for a more "
        "accurate computation. Format each question on its own line starting with '→'.\n"
        "Example: '→ What is your monthly rent? (needed for HRA exemption calculation)'\n\n"
    )

    # Build system prompt
    if len(agent_keys) == 1:
        primary = agent_instances[agent_keys[0]]
        system_prompt = awareness + primary.system_prompt
    else:
        combined_parts = [
            awareness +
            "Multi-domain financial query. Use ALL specialist briefings below for ONE unified answer.\n"
        ]
        for rk in agent_keys:
            ra = agent_instances[rk]
            label = AGENTS.get(rk, rk)
            combined_parts.append(f"=== {label} ===\n{ra.system_prompt}\n")
        combined_parts.append(
            "\nBullets/tables. ₹ Lakhs/Crores. No filler. End with actionable steps."
        )
        system_prompt = "\n".join(combined_parts)

    # Build history messages from checkpoint memory + profile
    history_messages = []
    if profile:
        profile_text = format_profile(profile)
        if profile_text:
            history_messages.append({
                "role": "user",
                "content": f"[USER FINANCIAL PROFILE from our conversation]\n{profile_text}"
            })
            history_messages.append({
                "role": "assistant",
                "content": "Noted. I'll use these details for personalized advice."
            })

    # Add recent exchanges from checkpoint
    past_exchanges = state.get("past_exchanges", [])
    for ex in past_exchanges[-3:]:  # last 3 exchanges
        history_messages.append({"role": "user", "content": ex["user"]})
        resp = ex["assistant"]
        if len(resp) > 800:
            resp = resp[:800] + "\n[... response continues ...]"
        history_messages.append({"role": "assistant", "content": resp})

    # Token budget check
    from config import RESPONSE_MAX_TOKENS, CONTEXT_BUDGET_RESERVE
    max_ctx = LLM_CONFIG["n_ctx"]
    max_response = RESPONSE_MAX_TOKENS
    available_chars = int((max_ctx - max_response - CONTEXT_BUDGET_RESERVE) * 3.5)
    hist_chars = sum(len(m["content"]) for m in history_messages)
    total_chars = len(system_prompt) + len(context) + len(query) + hist_chars

    if total_chars > available_chars:
        excess = total_chars - available_chars
        logger.warning(f"Token budget exceeded by ~{excess} chars. Trimming context.")

        # Strategy: trim knowledge reference first (it's background info),
        # then history, then pre-computed data last (most critical for accuracy)
        knowledge_start = context.find("═══ INDIAN FINANCE REFERENCE")
        knowledge_end = context.find("═══ END REFERENCE ═══")
        if knowledge_start != -1 and knowledge_end != -1:
            knowledge_block = context[knowledge_start:knowledge_end + len("═══ END REFERENCE ═══")]
            if len(knowledge_block) > excess + 200:
                # Trim knowledge to fit
                trimmed_knowledge = knowledge_block[:len(knowledge_block) - excess - 200]
                trimmed_knowledge += "\n[... knowledge trimmed to fit ...]\n═══ END REFERENCE ═══"
                context = context[:knowledge_start] + trimmed_knowledge + context[knowledge_end + len("═══ END REFERENCE ═══"):]
                logger.info(f"Trimmed knowledge section by ~{excess} chars")
            else:
                # Remove knowledge entirely, keep computed data
                context = context[:knowledge_start] + context[knowledge_end + len("═══ END REFERENCE ═══"):]
                logger.info(f"Removed knowledge section ({len(knowledge_block)} chars) to fit budget")
                # Recheck if still over
                total_chars = len(system_prompt) + len(context) + len(query) + hist_chars
                if total_chars > available_chars:
                    excess = total_chars - available_chars
                    if len(context) > excess + 200:
                        context = context[:len(context) - excess - 200] + "\n[... context trimmed ...]\n"
        elif len(context) > excess + 200:
            context = context[:len(context) - excess - 200] + "\n[... context trimmed to fit ...]\n"
        else:
            context = context[:max(500, len(context) // 2)] + "\n[... context trimmed ...]\n"
            remaining = available_chars - len(context) - len(query) - hist_chars
            if len(system_prompt) > remaining:
                system_prompt = system_prompt[:remaining - 100] + "\n[... prompt trimmed ...]\n"

    # ── Thinking mode directive ──
    # Claude-like behavior: think before answering on non-trivial queries.
    # GPU: moderate + complex get /think  |  CPU: only complex gets /think
    complexity = state.get("complexity", "moderate")
    from config import THINKING_ENABLED, IS_CPU_ONLY, THINKING_BUDGET_HINT
    _should_think = False
    if THINKING_ENABLED:
        if IS_CPU_ONLY:
            # CPU: only complex queries get thinking (saves time on moderate)
            _should_think = complexity == "complex"
        else:
            # GPU: moderate + complex queries get thinking
            _should_think = complexity in ("moderate", "complex")

    if _should_think:
        # Scale thinking budget by complexity
        if complexity == "complex":
            budget = THINKING_BUDGET_HINT
        else:
            budget = max(60, THINKING_BUDGET_HINT // 2)  # moderate = shorter thinking
        system_prompt += (
            f"\nThink step-by-step before answering. Structure your thinking as: "
            f"1) Identify what the user needs, 2) Key data/calculations to use, "
            f"3) Reasoning through the answer. Keep reasoning under {budget} words. /think"
        )
    else:
        system_prompt += " /no_think"

    return {
        "system_prompt": system_prompt,
        "context": context,
        "history_messages": history_messages,
    }


def generate_response_node(state: dict) -> dict:
    """Generate the LLM response (blocking, non-streaming — used for non-stream calls)."""
    from llm.engine import llm

    response = llm.generate(
        state["system_prompt"],
        state["query"],
        state["context"],
        state.get("history_messages", []),
    )

    # Update profile with new facts
    profile = state.get("profile", {})
    profile = extract_profile_facts(state["query"], profile)
    profile = extract_profile_facts(response, profile)

    # Update past exchanges
    past_exchanges = list(state.get("past_exchanges", []))
    past_exchanges.append({
        "user": state["query"],
        "assistant": response,
        "ts": time.time(),
    })

    return {
        "response": response,
        "profile": profile,
        "past_exchanges": past_exchanges,
    }


# ──────────────────────── Reflection Node ────────────────────────

_REFLECTION_PROMPT = """You are a financial response quality checker. Review the response below and determine if it adequately addresses ALL parts of the user's query.

User query: {query}

Response to evaluate:
{response}

Check for:
1. Does it address every sub-question or aspect the user asked about?
2. Are concrete ₹ numbers provided where calculations were expected?
3. Are actionable next steps included?
4. Is any major topic completely missing?

Return ONLY a JSON object:
- "pass": true if the response is adequate, false if it needs improvement
- "missing": brief description of what's missing (empty string if pass is true)

Example: {{"pass": true, "missing": ""}}
Example: {{"pass": false, "missing": "No comparison between old and new tax regime as asked"}}
"""


def reflect_node(state: dict) -> dict:
    """Evaluate response quality for complex queries.
    
    Only runs for complex queries. Uses a lightweight LLM call to check
    if the response covers all aspects of the user's question. If not,
    provides feedback for a refinement pass.
    """
    complexity = state.get("complexity", "moderate")
    response = state.get("response", "")
    query = state.get("query", "")
    
    # Only reflect on complex queries — simple/moderate don't need it
    if complexity != "complex":
        logger.info(f"Skipping reflection (complexity={complexity})")
        return {"reflection_pass": True, "refinement_needed": False}

    # Don't reflect if already refined (prevent infinite loops)
    if state.get("refinement_done"):
        logger.info("Already refined once — skipping further reflection")
        return {"reflection_pass": True, "refinement_needed": False}
    
    from llm.engine import llm
    
    try:
        prompt = _REFLECTION_PROMPT.format(
            query=query[:500],
            response=response[:2000],  # Cap to avoid token overflow
        )
        
        result = llm.model.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a precise JSON evaluator. Return ONLY valid JSON. /no_think"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            max_tokens=150,
        )
        
        raw = result["choices"][0]["message"]["content"].strip()
        raw = re.sub(r'<think>.*?</think>\s*', '', raw, flags=re.DOTALL).strip()
        
        # Parse JSON
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            passed = parsed.get("pass", True)
            missing = parsed.get("missing", "")
            
            if not passed and missing:
                logger.info(f"Reflection FAILED: {missing}")
                return {
                    "reflection_pass": False,
                    "refinement_needed": True,
                    "reflection_feedback": missing,
                }
            else:
                logger.info("Reflection PASSED — response is adequate")
                return {"reflection_pass": True, "refinement_needed": False}
        else:
            logger.warning(f"Reflection returned non-JSON: {raw[:100]}")
            return {"reflection_pass": True, "refinement_needed": False}
            
    except Exception as e:
        logger.warning(f"Reflection failed: {e}")
        return {"reflection_pass": True, "refinement_needed": False}


def refine_node(state: dict) -> dict:
    """Refine the response based on reflection feedback.
    
    Takes the original response + reflection feedback and asks the LLM
    to improve the response to address missing aspects.
    """
    from llm.engine import llm
    
    feedback = state.get("reflection_feedback", "")
    original_response = state.get("response", "")
    query = state.get("query", "")
    context = state.get("context", "")
    system_prompt = state.get("system_prompt", "")
    
    refinement_prompt = (
        f"{system_prompt}\n\n"
        f"IMPORTANT: Your previous response was reviewed and found to be missing: {feedback}\n"
        f"Please provide a COMPLETE improved response that addresses this gap.\n"
        f"Build on your previous answer — don't start from scratch.\n"
    )
    
    # Include the original response as context for refinement
    augmented_context = (
        f"{context}\n\n"
        f"YOUR PREVIOUS RESPONSE (improve upon this):\n{original_response[:3000]}\n\n"
        f"REVIEWER FEEDBACK: {feedback}"
    )
    
    refined = llm.generate(
        refinement_prompt,
        query,
        augmented_context,
        state.get("history_messages", []),
    )
    
    logger.info(f"Refined response: {len(refined)} chars (was {len(original_response)} chars)")
    
    # Update profile with refined response facts
    profile = state.get("profile", {})
    profile = extract_profile_facts(refined, profile)
    
    # Replace the response and mark refinement as done
    past_exchanges = list(state.get("past_exchanges", []))
    if past_exchanges and past_exchanges[-1].get("user") == query:
        past_exchanges[-1]["assistant"] = refined
    
    return {
        "response": refined,
        "profile": profile,
        "past_exchanges": past_exchanges,
        "refinement_done": True,
    }


# ──────────────────────── Routing Functions ────────────────────────

def _route_after_generate(state: dict) -> str:
    """Decide whether to reflect on the response or go straight to END.
    
    Only complex queries go through reflection — simple/moderate skip it.
    Reflection is disabled on CPU to save time.
    """
    from config import REFLECTION_ENABLED
    if not REFLECTION_ENABLED:
        return "__end__"
    complexity = state.get("complexity", "moderate")
    if complexity == "complex" and not state.get("refinement_done"):
        return "reflect"
    return "__end__"


def _route_after_reflect(state: dict) -> str:
    """Decide whether to refine the response or accept it.
    
    If reflection found gaps, route to refine node for improvement.
    """
    if state.get("refinement_needed"):
        return "refine"
    return "__end__"


# ──────────────────────── Build the Graph ────────────────────────

def build_graph(checkpointer=None):
    """Build and compile the FinanceGPT agentic workflow.
    
    Graph structure with conditional edges:
    
        START → route → gather_context → build_prompt → generate
                                                            ↓
                                              ┌─── (simple/moderate) ──→ END
                                              │
                                              └─── (complex) ──→ reflect
                                                                    ↓
                                                        ┌── (pass) ──→ END
                                                        └── (fail) ──→ refine → END
    """
    workflow = StateGraph(dict)

    # Add nodes
    workflow.add_node("route", route_node)
    workflow.add_node("gather_context", gather_context_node)
    workflow.add_node("build_prompt", build_prompt_node)
    workflow.add_node("generate", generate_response_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("refine", refine_node)

    # Linear path: route → gather → build → generate
    workflow.add_edge(START, "route")
    workflow.add_edge("route", "gather_context")
    workflow.add_edge("gather_context", "build_prompt")
    workflow.add_edge("build_prompt", "generate")

    # Conditional: after generate → reflect (complex) or END (simple/moderate)
    workflow.add_conditional_edges("generate", _route_after_generate, {
        "reflect": "reflect",
        "__end__": END,
    })

    # Conditional: after reflect → refine (if gaps found) or END (if adequate)
    workflow.add_conditional_edges("reflect", _route_after_reflect, {
        "refine": "refine",
        "__end__": END,
    })

    # Refine always goes to END (max 1 refinement pass)
    workflow.add_edge("refine", END)

    # Compile with checkpointer for session persistence
    return workflow.compile(checkpointer=checkpointer)


# ──────────────────────── Streaming Helper ────────────────────────

async def stream_workflow(
    graph,
    query: str,
    session_id: str,
    manual_agent: str = "auto",
    session_files: list = None,
):
    """
    Run the graph with streaming — yields events for the SSE endpoint.
    This wraps the graph execution and adds token-level streaming from the LLM.

    Yields dicts: {"event": str, "data": dict}
    """
    from llm.engine import llm

    config = {"configurable": {"thread_id": session_id}}

    # Load existing state from checkpoint
    existing_state = {}
    try:
        snapshot = await graph.aget_state(config)
        if snapshot and snapshot.values:
            existing_state = snapshot.values
    except Exception:
        pass

    profile = existing_state.get("profile", {})
    past_exchanges = existing_state.get("past_exchanges", [])

    # Run route + gather_context + build_prompt nodes first
    # We'll manually orchestrate to stream the LLM tokens
    input_state = {
        "query": query,
        "manual_agent": manual_agent,
        "session_files": session_files or [],
        "profile": profile,
        "past_exchanges": past_exchanges,
    }

    import queue
    timings = {}  # step -> seconds
    pipeline_start = time.time()

    # Pre-warm: kick off market prefetch + smart_calc in background while routing runs
    # Overlapping I/O with the LLM router call saves 1-3s total
    _prefetch_future = None
    _precalc_future = None
    try:
        from concurrent.futures import ThreadPoolExecutor
        _warmup_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="warmup")
        def _warm_market():
            try:
                from tools.market_prefetch import is_prefetch_ready
                if not is_prefetch_ready():
                    from tools.market_prefetch import _run_prefetch
                    _run_prefetch()
            except Exception:
                pass
        _prefetch_future = _warmup_pool.submit(_warm_market)
        # Pre-run smart_calc (doesn't depend on routing result)
        def _precalc():
            try:
                from tools.smart_calc import smart_calculate
                return smart_calculate(query, profile)
            except Exception:
                return None
        _precalc_future = _warmup_pool.submit(_precalc)
    except Exception:
        pass

    # Step 1: Route
    yield {"event": "status", "data": {"step": "routing", "message": "Analyzing your query..."}}
    t_step = time.time()
    route_result = route_node(input_state)
    timings["routing"] = round(time.time() - t_step, 2)
    input_state.update(route_result)

    # Yield agent info
    for info in route_result["agent_info"]:
        yield {"event": "agent", "data": info}

    yield {"event": "status", "data": {"step": "context", "message": "Gathering market data & context..."}}

    # Step 2: Gather context (may be slow — web/market calls)
    # Pass pre-computed smart_calc result to avoid redundant computation
    if _precalc_future:
        try:
            precalc_result = _precalc_future.result(timeout=5)
            if precalc_result:
                input_state["_precalc_result"] = precalc_result
        except Exception:
            pass
    t_step = time.time()
    ctx_result = await asyncio.to_thread(gather_context_node, input_state)
    timings["context_gathering"] = round(time.time() - t_step, 2)
    timings["context_subtimings"] = ctx_result.get("context_subtimings", {})
    input_state.update(ctx_result)

    yield {"event": "status", "data": {
        "step": "context_done",
        "message": f"Context ready ({len(ctx_result['context']):,} chars, {ctx_result['context_time']:.1f}s)"
    }}

    # Step 3: Build prompt
    t_step = time.time()
    prompt_result = build_prompt_node(input_state)
    timings["prompt_build"] = round(time.time() - t_step, 2)
    input_state.update(prompt_result)

    # Step 4: Stream LLM tokens
    yield {"event": "status", "data": {"step": "llm", "message": "Generating AI response..."}}

    t0 = time.time()
    ttft = None  # time to first token
    full_response = []
    token_count = 0

    token_queue = queue.Queue()
    stream_error = [None]

    def _run_stream():
        try:
            for token_data in llm.generate_stream(
                input_state["system_prompt"],
                input_state["query"],
                input_state["context"],
                input_state.get("history_messages", []),
            ):
                token_queue.put(token_data)  # (text, kind) tuple
            token_queue.put(None)  # sentinel
        except Exception as e:
            stream_error[0] = e
            token_queue.put(None)

    # Start streaming in background thread
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_stream)

    think_token_count = 0

    while True:
        from config import PER_TOKEN_TIMEOUT
        token_data = await asyncio.to_thread(token_queue.get, True, PER_TOKEN_TIMEOUT)
        if token_data is None:
            break
        text, kind = token_data
        if kind == "think":
            think_token_count += 1
            yield {"event": "thinking", "data": {"t": text}}
        else:
            token_count += 1
            if ttft is None:
                ttft = round(time.time() - t0, 2)
            full_response.append(text)
            yield {"event": "token", "data": {"t": text}}

    if stream_error[0]:
        yield {"event": "error", "data": {"message": str(stream_error[0])}}
        return

    response_text = "".join(full_response)
    inference_time = round(time.time() - t0, 2)

    timings["inference"] = inference_time
    timings["ttft"] = ttft or 0
    timings["tokens_out"] = token_count
    timings["think_tokens"] = think_token_count
    if inference_time > 0 and token_count > 0:
        timings["tokens_per_sec"] = round(token_count / inference_time, 1)

    # ── Step 5: Reflection + Refinement (complex queries only, GPU only) ──
    from config import REFLECTION_ENABLED
    complexity = input_state.get("complexity", "moderate")
    if REFLECTION_ENABLED and complexity == "complex":
        yield {"event": "status", "data": {"step": "reflecting", "message": "Reviewing response quality..."}}
        t_step = time.time()

        # Build state for reflection
        input_state["response"] = response_text
        reflect_result = await asyncio.to_thread(reflect_node, input_state)
        timings["reflection"] = round(time.time() - t_step, 2)
        input_state.update(reflect_result)

        if reflect_result.get("refinement_needed"):
            feedback = reflect_result.get("reflection_feedback", "")
            yield {"event": "status", "data": {
                "step": "refining",
                "message": f"Improving response: {feedback[:80]}..."
            }}

            # Stream the refined response (replaces the original)
            t_refine = time.time()
            refine_feedback = reflect_result.get("reflection_feedback", "")

            refinement_prompt = (
                f"{input_state['system_prompt']}\n\n"
                f"IMPORTANT: Your previous response was reviewed and found to be missing: {refine_feedback}\n"
                f"Please provide a COMPLETE improved response that addresses this gap.\n"
                f"Build on your previous answer — don't start from scratch.\n"
            )
            augmented_context = (
                f"{input_state['context']}\n\n"
                f"YOUR PREVIOUS RESPONSE (improve upon this):\n{response_text[:3000]}\n\n"
                f"REVIEWER FEEDBACK: {refine_feedback}"
            )

            # Clear previous tokens and stream refined response
            yield {"event": "clear", "data": {}}
            full_response = []
            token_count = 0
            ttft = None
            t0_refine = time.time()
            stream_error = [None]

            token_queue_refine = queue.Queue()

            def _run_refine_stream():
                try:
                    for token_data in llm.generate_stream(
                        refinement_prompt,
                        input_state["query"],
                        augmented_context,
                        input_state.get("history_messages", []),
                    ):
                        token_queue_refine.put(token_data)
                    token_queue_refine.put(None)
                except Exception as e:
                    stream_error[0] = e
                    token_queue_refine.put(None)

            loop.run_in_executor(None, _run_refine_stream)

            while True:
                token_data = await asyncio.to_thread(token_queue_refine.get, True, 120.0)
                if token_data is None:
                    break
                text, kind = token_data
                if kind == "think":
                    continue  # Skip think tokens in refinement pass
                token_count += 1
                if ttft is None:
                    ttft = round(time.time() - t0_refine, 2)
                full_response.append(text)
                yield {"event": "token", "data": {"t": text}}

            if stream_error[0]:
                yield {"event": "error", "data": {"message": str(stream_error[0])}}
                return

            response_text = "".join(full_response)
            timings["refinement"] = round(time.time() - t_refine, 2)
            timings["inference"] = inference_time + timings["refinement"]
            timings["ttft"] = ttft or 0
            timings["tokens_out"] = token_count
            timings["refined"] = True
            if timings["refinement"] > 0 and token_count > 0:
                timings["tokens_per_sec"] = round(token_count / timings["refinement"], 1)
            logger.info(f"Refinement: {len(response_text)} chars in {timings['refinement']}s")
        else:
            logger.info(f"Reflection passed — no refinement needed ({timings['reflection']}s)")

    total_time = round(time.time() - pipeline_start, 2)
    timings["total"] = total_time

    # Update profile with facts from this exchange
    updated_profile = extract_profile_facts(query, profile)
    updated_profile = extract_profile_facts(response_text, updated_profile)

    # Update past exchanges
    updated_exchanges = list(past_exchanges)
    updated_exchanges.append({
        "user": query,
        "assistant": response_text,
        "ts": time.time(),
    })
    # Keep only last 15 exchanges to prevent unbounded growth
    if len(updated_exchanges) > 15:
        updated_exchanges = updated_exchanges[-15:]

    # Save state to checkpoint
    final_node = "refine" if timings.get("refined") else "generate"
    final_state = {
        "query": query,
        "profile": updated_profile,
        "past_exchanges": updated_exchanges,
        "agent_keys": input_state["agent_keys"],
        "response": response_text,
        "complexity": input_state.get("complexity", "moderate"),
    }
    try:
        await graph.aupdate_state(config, final_state, as_node=final_node)
        logger.info(f"Checkpoint saved: session={session_id}, profile={len(updated_profile)} facts, "
                     f"exchanges={len(updated_exchanges)}")
    except Exception as e:
        logger.warning(f"Failed to save checkpoint: {e}")

    # Log timing summary BEFORE yielding done events (client may disconnect after done)
    reflection_str = f" reflection={timings.get('reflection', 0)}s" if complexity == "complex" else ""
    refinement_str = f" refinement={timings.get('refinement', 0)}s" if timings.get("refined") else ""
    logger.info(
        f"Pipeline timings: routing={timings['routing']}s context={timings['context_gathering']}s "
        f"prompt={timings['prompt_build']}s inference={timings['inference']}s "
        f"ttft={timings['ttft']}s tokens={token_count} "
        f"tok/s={timings.get('tokens_per_sec','?')} "
        f"complexity={complexity}{reflection_str}{refinement_str} total={total_time}s"
    )
    logger.info(f"Context subtimings: {timings.get('context_subtimings', {})}")

    yield {"event": "status", "data": {"step": "done", "message": f"Done in {total_time:.1f}s"}}
    yield {"event": "timing", "data": timings}
    yield {"event": "done", "data": {
        "time": total_time,
        "agent": input_state["agent_keys"][0],
    }}
