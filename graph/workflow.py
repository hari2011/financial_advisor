"""
LangGraph workflow for FinanceGPT.
Replaces the manual orchestration in server.py with a declarative graph.

Graph flow:
  route → gather_context (parallel per agent) → build_prompt → stream_llm

State carries everything: query, routed agents, context, profile, response tokens.
"""
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
    """Route query to appropriate agent(s) using keyword + LLM hybrid router."""
    query = state["query"]
    manual = state.get("manual_agent")

    manual_key = None if manual == "auto" else manual
    routed = route_query(query, manual_key)

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

    logger.info(f"Routed to: {agent_keys}")
    return {
        "agent_keys": agent_keys,
        "agent_instances": agent_instances,
        "agent_info": agent_info,
    }


def gather_context_node(state: dict) -> dict:
    """Gather context from all routed agents (parallel where safe)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    query = state["query"]
    agent_keys = state["agent_keys"]
    agent_instances = state["agent_instances"]
    session_files = state.get("session_files", [])
    profile = state.get("profile", {})

    t0 = time.time()
    all_contexts = []

    # ── Inject pre-cached market briefing (instant, no network call) ──
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
        return _timed("deep_research", lambda: deep_research(query, max_context_chars=5000))

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
        futures[pool.submit(_smart_calc)] = "smart_calc"
        futures[pool.submit(_deep_research)] = "deep_research"
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

        # Deep research fallback to shallow search
        if deep_research_result:
            all_contexts.append(deep_research_result)
        else:
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
    max_ctx = LLM_CONFIG["n_ctx"]
    max_response = LLM_CONFIG["max_tokens"]
    available_chars = int((max_ctx - max_response - 100) * 3.5)
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


# ──────────────────────── Build the Graph ────────────────────────

def build_graph(checkpointer=None):
    """Build and compile the FinanceGPT LangGraph workflow."""
    workflow = StateGraph(dict)

    # Add nodes
    workflow.add_node("route", route_node)
    workflow.add_node("gather_context", gather_context_node)
    workflow.add_node("build_prompt", build_prompt_node)
    workflow.add_node("generate", generate_response_node)

    # Define edges: linear pipeline
    workflow.add_edge(START, "route")
    workflow.add_edge("route", "gather_context")
    workflow.add_edge("gather_context", "build_prompt")
    workflow.add_edge("build_prompt", "generate")
    workflow.add_edge("generate", END)

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
            for token in llm.generate_stream(
                input_state["system_prompt"],
                input_state["query"],
                input_state["context"],
                input_state.get("history_messages", []),
            ):
                token_queue.put(token)
            token_queue.put(None)  # sentinel
        except Exception as e:
            stream_error[0] = e
            token_queue.put(None)

    # Start streaming in background thread
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_stream)

    while True:
        token = await asyncio.to_thread(token_queue.get, True, 120.0)
        if token is None:
            break
        token_count += 1
        if ttft is None:
            ttft = round(time.time() - t0, 2)
        full_response.append(token)
        yield {"event": "token", "data": {"t": token}}

    if stream_error[0]:
        yield {"event": "error", "data": {"message": str(stream_error[0])}}
        return

    response_text = "".join(full_response)
    inference_time = round(time.time() - t0, 2)
    total_time = round(time.time() - pipeline_start, 2)

    timings["inference"] = inference_time
    timings["ttft"] = ttft or 0
    timings["tokens_out"] = token_count
    if inference_time > 0 and token_count > 0:
        timings["tokens_per_sec"] = round(token_count / inference_time, 1)
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
    final_state = {
        "query": query,
        "profile": updated_profile,
        "past_exchanges": updated_exchanges,
        "agent_keys": input_state["agent_keys"],
        "response": response_text,
    }
    try:
        await graph.aupdate_state(config, final_state, as_node="generate")
        logger.info(f"Checkpoint saved: session={session_id}, profile={len(updated_profile)} facts, "
                     f"exchanges={len(updated_exchanges)}")
    except Exception as e:
        logger.warning(f"Failed to save checkpoint: {e}")

    # Log timing summary BEFORE yielding done events (client may disconnect after done)
    logger.info(
        f"Pipeline timings: routing={timings['routing']}s context={timings['context_gathering']}s "
        f"prompt={timings['prompt_build']}s inference={timings['inference']}s "
        f"ttft={timings['ttft']}s tokens={token_count} "
        f"tok/s={timings.get('tokens_per_sec','?')} total={total_time}s"
    )
    logger.info(f"Context subtimings: {timings.get('context_subtimings', {})}")

    yield {"event": "status", "data": {"step": "done", "message": f"Done in {total_time:.1f}s"}}
    yield {"event": "timing", "data": timings}
    yield {"event": "done", "data": {
        "time": total_time,
        "agent": input_state["agent_keys"][0],
    }}
