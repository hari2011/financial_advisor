# Architecture Guide

A deep dive into how FinanceGPT works — from user query to final response.

---

## Table of Contents

- [Design Philosophy](#design-philosophy)
- [System Overview](#system-overview)
- [Request Lifecycle](#request-lifecycle)
- [Component Deep Dives](#component-deep-dives)
  - [1. FastAPI Server](#1-fastapi-server)
  - [2. LLM Router](#2-llm-router)
  - [3. 10 Specialist Agents](#3-10-specialist-agents)
  - [4. LangGraph Pipeline](#4-langgraph-pipeline)
  - [5. LLM Engine](#5-llm-engine)
  - [6. Financial Calculators](#6-financial-calculators)
  - [7. Market Data Layer](#7-market-data-layer)
  - [8. Web Search & Research](#8-web-search--research)
  - [9. Knowledge Base](#9-knowledge-base)
  - [10. Session Persistence](#10-session-persistence)
- [Caching Architecture](#caching-architecture)
- [CPU vs GPU Pipeline](#cpu-vs-gpu-pipeline)
- [Hardware Auto-Detection](#hardware-auto-detection)
- [Data Flow Diagram](#data-flow-diagram)
- [File Structure](#file-structure)

---

## Design Philosophy

FinanceGPT uses a **hybrid architecture** — combining autonomous LLM decision-making with deterministic financial computation.

### Why hybrid?

Financial calculations must be **exact and reproducible**:
- SIP of ₹10K/month at 12% for 20 years = **₹99,91,479** (every time, exactly)
- Income tax on ₹15 LPA under new regime = **₹1,45,600** (exactly, per IT Act)

A fully autonomous LLM agent (like ReAct) might:
- Skip a calculation it deems "unnecessary"
- Compute SIP differently each time
- Hallucinate a tax amount

That's dangerous when people make real investment decisions based on the output.

### The FinanceGPT approach

```
┌─────────────────────────────────────────────────────┐
│ LLM (Agentic Layer)           │  "WHAT to compute"  │
│ • Understands user intent     │                     │
│ • Selects right agent(s)      │  Smart, adaptive    │
│ • Decides query complexity    │  but NOT trusted    │
│ • Generates natural language  │  with exact numbers │
├─────────────────────────────────────────────────────┤
│ Calculators (Deterministic)   │  "HOW to compute"   │
│ • 36 verified formulas        │                     │
│ • Cross-referenced against    │  Exact, verified,   │
│   Groww, ClearTax, ET Money   │  reproducible       │
│ • LLM cites these numbers     │                     │
└─────────────────────────────────────────────────────┘
```

**Result**: You get the intelligence of an agent (understanding context, comparing options, explaining trade-offs) with the reliability of a calculator (exact ₹ values, verified formulas).

---

## System Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                        Browser (index.html)                       │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Chat UI  │  │ Calculator   │  │ Market   │  │ File Upload  │ │
│  │ (SSE)    │  │ Grid (36)    │  │ Ticker   │  │ (CSV/PDF)    │ │
│  └────┬─────┘  └──────┬───────┘  └────┬─────┘  └──────┬───────┘ │
└───────┼────────────────┼───────────────┼────────────────┼─────────┘
        │                │               │                │
  ┌─────▼────────────────▼───────────────▼────────────────▼─────────┐
  │                   FastAPI Server (server.py)                     │
  │                                                                  │
  │  POST /api/chat ───────► LangGraph Pipeline (workflow.py)        │
  │  POST /api/calculate ──► Calculator Registry (calculator_reg.)   │
  │  GET  /api/market/* ───► Live Market Data (live_market.py)       │
  │  POST /api/upload ─────► File Parser (file_parser.py)            │
  │  GET  /api/health ─────► System + Cache Stats                    │
  └──────────────────────────────────────────────────────────────────┘
        │
  ┌─────▼──────────────────────────────────────────────────────────┐
  │              LangGraph Agentic Pipeline                         │
  │                                                                 │
  │  ┌──────┐   ┌─────────────┐   ┌────────────┐   ┌──────────┐  │
  │  │Route │──►│   Gather     │──►│   Build    │──►│ Generate │  │
  │  │Query │   │   Context    │   │   Prompt   │   │ Response │  │
  │  └──────┘   └─────────────┘   └────────────┘   └────┬─────┘  │
  │   LLM         Parallel:         /think or           │         │
  │   classifies   • Calculators    /no_think        ┌──▼──┐     │
  │   agents +     • Market data                     │Done?│     │
  │   complexity   • Web search                      └──┬──┘     │
  │                • Deep research     ┌──────────────┐  │        │
  │                                    │   Reflect    │◄─┘ GPU    │
  │                                    │   + Refine   │  complex  │
  │                                    └──────────────┘  only     │
  └─────────────────────────────────────────────────────────────────┘
        │
  ┌─────▼──────────────────────────────────────────────────────────┐
  │                   LLM Engine (engine.py)                        │
  │                                                                 │
  │  Qwen3-8B via llama-cpp-python                                 │
  │  • Metal (Apple Silicon) / CUDA (NVIDIA) / Vulkan (AMD) / CPU  │
  │  • KV cache quantization (Q8_0 GPU, Q4_0 CPU)                 │
  │  • Flash attention (GPU only)                                   │
  │  • Response cache (64 entries, 10-min TTL)                     │
  └─────────────────────────────────────────────────────────────────┘
```

---

## Request Lifecycle

Here's exactly what happens when you type a question:

### Example: "SIP of ₹10K per month for 20 years at 12% — is it worth it?"

```
1. BROWSER → POST /api/chat
   Body: { query: "SIP of ₹10K per month for 20 years at 12%...", session_id: "abc123" }

2. SERVER creates SSE stream
   → Sends event: { type: "session", session_id: "abc123" }

3. LANGGRAPH PIPELINE starts

   ┌─ Step 1: ROUTE (1-3s) ───────────────────────────────────────┐
   │  Router LLM analyzes the query:                               │
   │  • Agents selected: ["mutual_fund_advisor", "general_advisor"]│
   │  • Complexity: "moderate"                                     │
   │  • Search queries: ["current top SIP funds India 2026"]       │
   │  → Sends event: { type: "agent", agents: [...] }             │
   └───────────────────────────────────────────────────────────────┘
                              ↓
   ┌─ Step 2: GATHER CONTEXT (1-5s, parallel) ────────────────────┐
   │  All these run simultaneously:                                │
   │  • Smart Calculator → detects "SIP" → runs sip_calculator    │
   │    → Result: ₹99,91,479 corpus, 10x multiplier               │
   │  • Market Data → Gold 24K, Nifty 50, repo rate               │
   │  • Web Search → "current top SIP funds India 2026"           │
   │  • Agent context → mutual_fund_advisor system prompt          │
   │  → Sends event: { type: "status", step: "gathering..." }     │
   └───────────────────────────────────────────────────────────────┘
                              ↓
   ┌─ Step 3: BUILD PROMPT ────────────────────────────────────────┐
   │  Assembles the full system prompt:                            │
   │  • Agent expertise (mutual fund + general)                    │
   │  • Pre-computed calculations (₹99,91,479 SIP result)         │
   │  • Market data snapshot                                       │
   │  • Web search results                                         │
   │  • User profile (if known: age, income, risk level)           │
   │  • Adds /no_think (moderate query, not complex)               │
   │  • Trims to fit context window budget                         │
   └───────────────────────────────────────────────────────────────┘
                              ↓
   ┌─ Step 4: GENERATE (5-20s) ───────────────────────────────────┐
   │  LLM generates response token by token:                       │
   │  → Sends event: { type: "token", content: "A" }              │
   │  → Sends event: { type: "token", content: " SIP" }           │
   │  → Sends event: { type: "token", content: " of" }            │
   │  → ... (streamed in real-time to browser)                     │
   │                                                               │
   │  The LLM references the pre-computed ₹99,91,479 value        │
   │  (never hallucinates numbers — they're in the prompt)         │
   └───────────────────────────────────────────────────────────────┘
                              ↓
   ┌─ Step 5: DONE ───────────────────────────────────────────────┐
   │  → Sends event: { type: "done", timing: { route: 1.2s, ... }}│
   │  → Profile extraction: saves any facts (age, income, goals)   │
   │  → Response cached for duplicate queries (10-min TTL)         │
   └───────────────────────────────────────────────────────────────┘
```

### What's different for complex queries (GPU only)?

For queries like "Compare old vs new tax regime for ₹25 LPA with HRA ₹15K and 80C ₹1.5L":

- **Complexity = "complex"** → triggers extended pipeline
- **Thinking mode**: Adds `/think` → LLM first reasons internally (visible in UI "thinking" block)
- **Deep research**: More extensive web search (7K chars vs 3.5K)
- **Reflection**: After generating, a lightweight LLM pass checks quality
- **Refinement**: If reflection finds gaps, LLM generates an improved response

---

## Component Deep Dives

### 1. FastAPI Server

**File**: `server.py`

The HTTP layer connecting the browser to the AI pipeline.

| Responsibility | Details |
|---------------|---------|
| SSE streaming | Token-by-token response delivery via Server-Sent Events |
| Session management | SQLite database for chat history, file uploads, session metadata |
| Static files | Serves `index.html`, `style.css`, `logo.svg` |
| CORS | Enabled for all origins (local development) |
| Lifespan events | Pre-loads LLM, starts market prefetch, initializes databases |

**Key SSE event types:**

| Event | Purpose |
|-------|---------|
| `session` | Session ID for the conversation |
| `status` | Pipeline progress messages ("Analyzing query...", "Gathering data...") |
| `agent` | Which agents were selected for this query |
| `thinking` | LLM internal reasoning (complex queries, GPU only) |
| `token` | One token of the response (streamed) |
| `done` | Completion signal with timing breakdown |
| `error` | Error message if something fails |

---

### 2. LLM Router

**File**: `agents/router.py`

The "brain" that decides which agents handle each query.

**How it works:**

1. Takes the user's query
2. Sends it to the LLM with a classification prompt
3. LLM returns: agents (1-3), complexity level, search queries
4. Result is cached for 5 minutes (similar queries reuse the classification)

**Agent Dependency Graph:**

```
stock_analyst ←──── portfolio_manager ←──── retirement_planner
     │                    │                        │
     ▼                    ▼                        ▼
mutual_fund_advisor  tax_advisor              loan_advisor
                         │
                         ▼
                   budget_planner
                         │
                         ▼
                  insurance_advisor
                         │
                         ▼
                   crypto_analyst

general_advisor (standalone — handles anything not covered above)
```

The router understands these relationships. A query about "Should I prepay my home loan or invest in SIP?" routes to **both** `loan_advisor` and `mutual_fund_advisor`.

**Complexity classification:**

| Level | Example | Pipeline Behavior |
|-------|---------|-------------------|
| `simple` | "What is SIP?" | Skip web search, fast response |
| `moderate` | "SIP of ₹10K for 20 years" | Standard web search, calculators |
| `complex` | "Compare old vs new tax regime with detailed analysis" | Deep research, thinking mode, reflection |

---

### 3. 10 Specialist Agents

**Directory**: `agents/`

Each agent is a Python class inheriting from `BaseAgent`:

| Agent | File | Expertise |
|-------|------|-----------|
| Stock Market Analyst | `stock_analyst.py` | NSE/BSE stocks, indices, fundamentals (P/E, ROE, ROCE) |
| Mutual Fund Advisor | `mutual_fund_advisor.py` | SEBI categories, SIP planning, ELSS, direct vs regular |
| Portfolio Manager | `portfolio_manager.py` | Asset allocation, diversification, rebalancing, SGBs |
| Tax Advisor | `tax_advisor.py` | Income tax (new/old regime FY25-26), 80C/80D, HRA, CTC |
| Retirement Planner | `retirement_planner.py` | EPF, PPF, NPS, FIRE (5 types), corpus planning |
| Loan & EMI Advisor | `loan_advisor.py` | Home loan, EMI, prepayment, PMAY, CIBIL |
| Budget Planner | `budget_planner.py` | 50/30/20 rule in ₹, emergency fund, savings rate |
| Crypto Analyst | `crypto_analyst.py` | BTC/ETH prices, India crypto tax (30% + 1% TDS) |
| Insurance Advisor | `insurance_advisor.py` | Term life, health insurance, IRDAI, claim ratios |
| General Advisor | `general_advisor.py` | Catch-all for general financial guidance |

**Each agent provides:**
- A specialized system prompt with deep domain expertise
- Context-gathering logic (which calculators to run, what market data to fetch)
- Indian-market awareness (₹ formatting, Lakhs/Crores, SEBI/RBI/IRDAI references)

**Base agent capabilities** (inherited by all agents, from `base.py`):
- `fmt_inr()` — Format amounts in Indian notation (₹1.5L, ₹2.3Cr)
- `_auto_market_data()` — Inject current gold (24K/22K/18K), forex, index prices
- Web search and news search integration

---

### 4. LangGraph Pipeline

**File**: `graph/workflow.py`

The agentic orchestration engine using LangGraph's state graph.

**Pipeline stages:**

```python
# Simplified representation of the actual graph
StateGraph(PipelineState)
    .add_node("route", route_node)              # Classify query
    .add_node("gather_context", context_node)    # Parallel data gathering
    .add_node("build_prompt", prompt_node)        # Assemble system prompt
    .add_node("generate", generate_node)          # Stream LLM response
    .add_node("reflect", reflect_node)            # Quality check (GPU only)
    .add_node("refine", refine_node)              # Improve response (if needed)
    .add_edge(START, "route")
    .add_edge("route", "gather_context")
    .add_edge("gather_context", "build_prompt")
    .add_edge("build_prompt", "generate")
    .add_conditional_edges("generate",            # Dynamic routing:
        route_after_generate,                     # • simple/moderate → END
        {"reflect": "reflect", END: END})         # • complex (GPU) → reflect
    .add_conditional_edges("reflect",
        route_after_reflect,                      # • pass → END
        {"refine": "refine", END: END})           # • fail → refine
    .add_edge("refine", END)
```

**State object** (carried through entire pipeline):

| Field | Type | Purpose |
|-------|------|---------|
| `query` | str | User's original question |
| `agents` | list[str] | Selected agent IDs |
| `complexity` | str | simple / moderate / complex |
| `search_queries` | list[str] | LLM-generated search terms |
| `context` | dict | Gathered data (calcs, market, web) |
| `system_prompt` | str | Final assembled prompt |
| `response` | str | LLM's response |
| `profile` | dict | Extracted user facts (age, income, goals) |
| `timing` | dict | Per-step timing breakdown |

**Session persistence**: LangGraph state is checkpointed to SQLite after every step. If the server restarts mid-conversation, history is preserved.

---

### 5. LLM Engine

**File**: `llm/engine.py`

The inference layer wrapping llama-cpp-python.

**Key features:**

| Feature | Detail |
|---------|--------|
| Singleton | One `Llama` instance shared across all requests |
| KV cache | Q8_0 quantization (GPU) or Q4_0 (CPU) — saves 50-75% memory |
| Flash attention | Enabled on supported backends (Metal, CUDA) |
| Response cache | LRU (64 entries, 10-min TTL) — instant for repeated queries |
| Streaming | Token-by-token generation yielded to FastAPI SSE |
| Model discovery | Auto-finds GGUF in `models/`, auto-converts SafeTensors/PyTorch |

**Response cache flow:**

```
Query arrives
    │
    ▼
Hash(messages) → SHA-256 key
    │
    ▼
Cache hit? ─── Yes ──► Return cached response (instant)
    │
    No
    ▼
Generate response → Store in cache → Return
```

---

### 6. Financial Calculators

**Files**: `tools/financial_calc.py`, `tools/calculator_registry.py`, `tools/smart_calc.py`

Three layers working together:

```
User query: "SIP of ₹10K for 20 years at 12%"
    │
    ▼
Smart Dispatcher (smart_calc.py)
    • Regex + topic detection
    • Extracts: monthly=10000, rate=12%, years=20
    • Maps to: "sip" calculator
    │
    ▼
Calculator Registry (calculator_registry.py)
    • Validates inputs (type, min, max, required)
    • Calls the function
    • Formats output
    • Caches result (5-min TTL)
    │
    ▼
Calculator Implementation (financial_calc.py)
    • sip_calculator(10000, 12, 20)
    • Returns: {
        corpus: 9991479,
        invested: 2400000,
        wealth_gained: 7591479,
        wealth_multiplier: "4.16x",
        ...
      }
```

**36 calculators organized by category:**

| Category | Calculators | Count |
|----------|------------|-------|
| Investment & Savings | SIP, Lumpsum, Step-up SIP, Goal SIP, SIP vs Lumpsum, MF Returns, Compound Interest, Simple Interest, XIRR | 9 |
| Government Schemes | PPF, SSY, EPF, NPS, NSC, SCSS, Post Office MIS, APY, KVP | 9 |
| Fixed Income | FD, RD | 2 |
| Loans | EMI, Education Loan, Loan Prepayment, Flat vs Reducing | 4 |
| Tax | Income Tax, CTC, Capital Gains, HRA, GST, TDS, Gratuity | 7 |
| Planning | Retirement, FIRE (5 types), Inflation Goal, Salary Hike, SWP | 5 |

**Accuracy guarantee**: Every calculator has been cross-referenced against production platforms (Groww, ClearTax, ET Money, India Post). The test suite (`test_cross_ref.py`) has 53 test cases that must all pass.

---

### 7. Market Data Layer

**Files**: `tools/live_market.py`, `tools/market_prefetch.py`, `tools/market_data.py`

Real-time financial data from yfinance (no API keys).

**Data available:**

| Data | Source | Refresh |
|------|--------|---------|
| Nifty 50, Sensex, Bank Nifty | yfinance (^NSEI, ^BSESN) | Per-request |
| Individual stocks (NSE/BSE) | yfinance (RELIANCE.NS, TCS.NS) | Per-request |
| Gold prices (24K, 22K, 18K) | COMEX GC=F × USD/INR, purity calc | Per-request |
| Silver, Crude Oil | yfinance (SI=F, CL=F) | Per-request |
| USD/INR, EUR/INR, GBP/INR | yfinance (USDINR=X) | Per-request |
| Crypto (BTC, ETH) | yfinance (BTC-USD) | Per-request |
| Mutual Fund NAVs | mfapi.in | Per-request |
| FD/PPF/EPF/Repo rates | Knowledge base | Static (updated per release) |

**Gold purity calculations:**
- 24K (pure gold) = COMEX GC=F price × USD/INR rate
- 22K (standard Indian jewelry) = 24K × 22/24 (91.67% pure)
- 18K (premium jewelry) = 24K × 18/24 (75% pure)

**Market prefetch**: A background thread pre-fetches standard market data (indices, gold, forex) at server startup and refreshes hourly. When a query needs market data, it's already cached — eliminating the 1-3s yfinance fetch delay.

---

### 8. Web Search & Research

**Files**: `tools/web_search.py`, `tools/deep_research.py`

**Web search** (DuckDuckGo, no API key):
- Text search with rate limiting (0.5s between requests)
- News search (1.75s between requests)
- Result caching (10-min TTL)
- Fallback: HTML scraping if API is rate-limited

**Deep research** (for complex queries):
- Searches multiple queries generated by the router
- Fetches full web pages and extracts content
- Produces citation cards (`[1]`, `[2]`, `[3]`) with source domains
- Limited by `DEEP_RESEARCH_MAX_CHARS` config (7K GPU, 3.5K CPU)

---

### 9. Knowledge Base

**File**: `knowledge/indian_finance.py`

Static reference data for Indian financial regulations:

| Section | Contents |
|---------|----------|
| Tax slabs | New regime (FY 2025-26), Old regime, rebate u/s 87A |
| Section 80C | ₹1.5L limit — PPF, ELSS, NSC, NPS, insurance, tuition |
| Section 80D | ₹25K self, ₹50K parents (senior citizen) |
| EPF rules | 12% employee + 12% employer (3.67% EPF + 8.33% EPS) |
| CTC breakdown | Basic (40-50%), HRA (40-50% of basic), special allowance |
| NPS | Tier I/II, 80CCD(1B) additional ₹50K deduction |
| PPF | 7.1% tax-free, 15-year lock-in, partial withdrawal |
| Investment comparison | Risk, returns, tax, liquidity across all instruments |

---

### 10. Session Persistence

**Directory**: `sessions/`

Two SQLite databases:

| Database | Purpose |
|----------|---------|
| `checkpoints.db` | LangGraph state checkpoints — pipeline state preserved across restarts |
| `session_meta.db` | Chat metadata — session titles, timestamps, message history, pinned status |

**Auto-purge**: Keeps the 5 most recent unpinned sessions. Pinned sessions never expire.

**Profile extraction**: The LLM extracts user facts (age, income, risk appetite, goals) from conversations and stores them in session state. These persist across turns, enabling personalized advice.

---

## Caching Architecture

Five-layer caching stack for optimal performance:

```
Layer 1: KV Cache (in-memory, per-session)
  └─ Quantized key-value tensors (Q8_0 GPU / Q4_0 CPU)
  └─ Automatic prompt prefix reuse across turns

Layer 2: Response Cache (in-memory, 10-min TTL)
  └─ SHA-256(messages) → full response
  └─ 64 entries max, LRU eviction
  └─ Identical questions return instantly

Layer 3: Router Cache (in-memory, 5-min TTL)
  └─ Normalized query → classification result
  └─ 32 entries max
  └─ Similar queries skip LLM router

Layer 4: Calculator Cache (in-memory, 5-min TTL)
  └─ MD5(calc_id + inputs) → result
  └─ 256 entries max
  └─ Same calculation returns instantly

Layer 5: Market Data Cache (background, 1-hour refresh)
  └─ Pre-fetched indices, gold, forex
  └─ Warm data available when queries arrive
```

**Cache monitoring**: `GET /api/health` returns current cache sizes and hit/miss counts.

---

## CPU vs GPU Pipeline

The app auto-detects hardware and configures the pipeline:

```
                    GPU Pipeline (Full)                 CPU Pipeline (Lean)
                    ─────────────────                   ──────────────────
Query              →  Route (LLM)                    →  Route (LLM)
                   →  Gather Context (deep)           →  Gather Context (light)
                   →  Build Prompt + /think           →  Build Prompt + /no_think
                   →  Generate (4096 tokens max)      →  Generate (1536 tokens max)
                   →  Reflect (quality check)         →  ── skipped ──
                   →  Refine (if needed)              →  ── skipped ──
                   →  Done                            →  Done
```

**Detailed comparison:**

| Setting | CPU (Lean) | GPU (Full) |
|---------|-----------|------------|
| Model file | Q4_K_M (4.6 GB) | Q5_K_M (5.5 GB) |
| KV cache quantization | Q4_0 (~75% savings) | Q8_0 (~50% savings) |
| Flash attention | Disabled | Enabled |
| Max response tokens | 1,536 | 4,096 |
| Router max tokens | 100 | 150 |
| Deep research context | 3,500 chars | 7,000 chars |
| Thinking mode (`/think`) | Disabled | Enabled (complex queries) |
| Reflection + refinement | Disabled | Enabled (complex queries) |
| Context budget reserve | 200 tokens | 100 tokens |
| Typical response time | 15-40s | 5-15s |

> **Important**: CPU mode is not degraded — it's **optimized**. The same core functionality (agents, calculators, market data, search) is available. The pipeline is trimmed to avoid the most time-consuming steps (reflection, thinking) that would make CPU wait times unbearable.

---

## Hardware Auto-Detection

**File**: `platform_setup.py`

Runs automatically at import time. No manual configuration needed.

**Detection chain:**

```
1. Operating System
   └─ macOS (Darwin) / Linux / Windows

2. Architecture
   └─ arm64 (Apple Silicon, ARM Linux) / x86_64 (Intel/AMD)

3. GPU Detection (in order, first match wins)
   ├─ macOS arm64 → Metal (always available on Apple Silicon)
   ├─ macOS Intel → check system_profiler for Metal support
   ├─ nvidia-smi exists → CUDA
   ├─ vulkaninfo exists → Vulkan
   └─ None found → CPU fallback

4. RAM Detection
   └─ Total system memory in MB

5. Auto-Scaling
   ├─ Context window: 4K - 32K tokens (based on RAM + GPU)
   ├─ GPU layers: -1 (all on GPU) or partial offload
   ├─ Threads: ~70-80% of CPU cores
   ├─ Batch size: 512 (CPU) or 1024 (GPU)
   └─ Max output tokens: 1536 (CPU) or 2048-4096 (GPU)
```

**Startup banner** (printed when server starts):

```
╔══════════════════════════════════════════════════╗
║          FinanceGPT — System Detection           ║
╠══════════════════════════════════════════════════╣
║  OS          : Darwin (arm64)                    ║
║  RAM         : 18,432 MB (18 GB)                 ║
║  GPU Backend : METAL                             ║
║  GPU Name    : Apple M3 Pro                      ║
║  Context     : 24,576 tokens                     ║
║  Max Output  : 4,096 tokens                      ║
║  Batch Size  : 1024                              ║
║  Pipeline    : GPU-accelerated (full)            ║
╚══════════════════════════════════════════════════╝
```

---

## Data Flow Diagram

### Chat Request

```
Browser ──POST /api/chat──► FastAPI
                              │
                              ▼
                         SSE Stream
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    ┌────▼────┐        ┌─────▼─────┐        ┌────▼────┐
    │  Router  │        │ Calculator│        │ Market  │
    │  (LLM)  │        │ Dispatch  │        │ Prefetch│
    └────┬────┘        └─────┬─────┘        └────┬────┘
         │                   │                    │
         ▼                   ▼                    ▼
    Agent selection    Pre-computed ₹      Live prices
    + complexity       values injected     (gold, stocks,
    + search queries   into prompt         forex, indices)
         │                   │                    │
         └────────┬──────────┘────────────────────┘
                  ▼
           Build System Prompt
                  │
                  ▼
            LLM Generate ────► Token stream ────► Browser
                  │
                  ▼ (GPU + complex)
            Reflect → Refine → Token stream ────► Browser
```

### Calculator Request

```
Browser ──POST /api/calculate──► FastAPI
                                    │
                                    ▼
                              Validate Inputs
                              (type, min, max)
                                    │
                                    ▼
                              Run Calculator
                              (deterministic ₹)
                                    │
                                    ▼
                              Format + Cache
                                    │
                                    ▼
                              JSON Response ──► Browser
```

---

## File Structure

```
financial_advisor/
│
├── start.py                 ← Entry point: one-command setup + launch
├── server.py                ← FastAPI server (SSE streaming, REST APIs)
├── config.py                ← All configuration (auto-detected + overrides)
├── platform_setup.py        ← Hardware detection (OS, GPU, RAM, cores)
├── setup_model.py           ← Model downloader (HuggingFace)
├── requirements.txt         ← Python dependencies
├── test_cross_ref.py        ← 53 accuracy tests (Groww, ClearTax verified)
│
├── graph/
│   └── workflow.py          ← LangGraph pipeline (route → context → prompt → generate → reflect)
│
├── llm/
│   └── engine.py            ← LLM inference engine (Llama wrapper, cache, streaming)
│
├── agents/
│   ├── base.py              ← BaseAgent class (shared methods, market data injection)
│   ├── router.py            ← LLM query router (classification, caching, dependency graph)
│   ├── stock_analyst.py     ← NSE/BSE stock analysis
│   ├── mutual_fund_advisor.py ← Mutual fund recommendations
│   ├── portfolio_manager.py ← Asset allocation strategy
│   ├── tax_advisor.py       ← Income tax planning (new/old regime)
│   ├── retirement_planner.py ← Retirement + FIRE planning
│   ├── loan_advisor.py      ← EMI + loan prepayment analysis
│   ├── budget_planner.py    ← Budget planning in ₹
│   ├── crypto_analyst.py    ← Crypto analysis (India tax rules)
│   ├── insurance_advisor.py ← Insurance recommendations
│   └── general_advisor.py   ← General financial guidance
│
├── tools/
│   ├── financial_calc.py    ← 36 calculator implementations (2500+ lines)
│   ├── calculator_registry.py ← Calculator definitions, validation, caching
│   ├── smart_calc.py        ← Auto-dispatcher (detects calc needs from query)
│   ├── live_market.py       ← Real-time market data (yfinance)
│   ├── market_prefetch.py   ← Background market data pre-fetch
│   ├── market_data.py       ← Legacy market data wrappers
│   ├── deep_research.py     ← Multi-source web research with citations
│   ├── web_search.py        ← DuckDuckGo search (thread-safe, cached)
│   ├── file_parser.py       ← CSV/PDF/Excel/JSON/TXT parser
│   └── model_converter.py   ← SafeTensors/PyTorch → GGUF converter
│
├── knowledge/
│   └── indian_finance.py    ← Indian finance reference data (tax slabs, EPF, 80C)
│
├── static/
│   ├── index.html           ← Full chat UI (SSE, calculators, ticker, themes)
│   ├── style.css            ← Styles (dark/light themes, responsive)
│   └── logo.svg             ← App logo
│
├── models/                  ← Downloaded .gguf model files (~5 GB)
├── sessions/                ← SQLite databases (checkpoints, session metadata)
├── uploads/                 ← User-uploaded files (CSV, PDF, Excel)
└── docs/                    ← Documentation (you are here)
```
