# 💹 FinanceGPT — Agentic AI Financial Advisor

A **100% local, privacy-first** agentic AI financial advisor powered by **Qwen3-8B** (via llama-cpp-python) and **LangGraph**, tailored for the **Indian market**. Runs on **macOS, Linux, and Windows** with automatic hardware detection and optimization.

All processing happens on your machine — your financial data never leaves your computer.

---

## ✨ Key Highlights

### AI & LLM
- **Qwen3-8B Q5_K_M** — 5-bit quantized (5.5 GB), runs locally via llama-cpp-python
- **10 specialist AI agents** — auto-routed via LLM classifier with agent dependency graph
- **Agentic LangGraph pipeline** — conditional edges, self-reflection, and adaptive tool selection
- **Query complexity classification** — LLM classifies queries as simple/moderate/complex to optimize the pipeline path
- **Self-reflection loop** — complex queries trigger automatic response quality evaluation and refinement
- **Adaptive context gathering** — simple queries skip expensive web search; complex queries get deeper research
- **Multi-agent collaboration** — complex queries route to multiple agents for a unified answer
- **Qwen3 non-thinking mode** — `/no_think` for fast, direct responses without chain-of-thought overhead

### Performance & Caching
- **KV cache quantization (Q8_0)** — reduces KV cache memory by ~50%, freeing ~1 GB RAM at 24K context
- **Flash attention** — 20-30% faster prompt processing (prefill), supported on Metal and CUDA
- **Response cache** — LRU cache (64 entries, 10-min TTL) for `generate()` — instant repeat answers
- **Calculator result cache** — LRU with 5-min TTL on all 36 calculators (same inputs = cached output)
- **Prompt prefix caching** — automatic via singleton `Llama` object; shared system prompt KV reused across turns
- **Parallel context gathering** — market data, web search, deep research, and agent context all run concurrently

### Financial Engine
- **36 financial calculators** — SIP, EMI, FD, PPF, NPS, EPF, SSY, FIRE (5 types), capital gains, HRA, CTC, and more
- **Cross-referenced accuracy** — all formulas verified against Groww, ClearTax, ET Money, India Post (53/53 tests pass)
- **Smart Calculator Dispatcher** — auto-detects computation needs from natural language and pre-computes ₹ values
- **Enhanced calculator outputs** — wealth multiplier, delay costs, real returns, tax-optimized tips, cross-product comparisons

### Data & Research
- **Real-time market data** — yfinance for NSE/BSE stocks, indices, gold, crypto (no API keys)
- **Deep research** — multi-source web research with Perplexity-style `[1]` citation cards
- **Knowledge base** — Indian finance reference (tax slabs, 80C limits, NPS rules, EPF rates)
- **File upload** — CSV, PDF, Excel, JSON, TXT parsed and injected into context

### UI & UX
- **Modern chat UI** — streaming tokens, syntax highlighting (highlight.js), math rendering (KaTeX)
- **36-calculator grid** — searchable, with input forms, instant results, and rich output formatting
- **Light / Dark themes** — toggle with persistence
- **Stop / Regenerate / Feedback** — full conversation control
- **Export to Markdown** — download entire chat history
- **Pipeline timing** — per-step performance breakdown on every response

### Infrastructure
- **Cross-platform** — macOS (Apple Silicon + Intel), Linux (CUDA/Vulkan), Windows
- **Auto GPU detection** — Metal → CUDA → Vulkan → CPU fallback
- **Auto scaling** — context window, GPU layers, threads tuned to your hardware
- **Session persistence** — conversation history + user profile via SQLite checkpointing
- **Privacy** — zero API keys, zero telemetry, zero cloud calls

---

## 🖥️ System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 8 GB | 16 GB+ |
| **Disk** | 8 GB free | 12 GB free |
| **CPU** | Any 64-bit | Apple Silicon / modern x86 |
| **GPU** | Not required | Apple Metal / NVIDIA CUDA / AMD Vulkan |
| **OS** | macOS 12+, Ubuntu 20.04+, Windows 10+ | macOS 14+ (Apple Silicon) |
| **Python** | 3.10+ | 3.11+ |

---

## 🚀 Quick Start

### Step 1 — Clone & Setup Python

```bash
git clone <repo-url>
cd financial_advisor

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate        # macOS / Linux
# .\venv\Scripts\Activate.ps1   # Windows PowerShell
```

### Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Install llama-cpp-python (Platform-Specific)

This is the only step that differs by OS/GPU. Pick your platform:

<details>
<summary><strong>macOS — Apple Silicon (M1/M2/M3/M4) ✅ Recommended</strong></summary>

```bash
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```
Metal GPU acceleration enabled. All model layers offloaded to GPU.
</details>

<details>
<summary><strong>macOS — Intel</strong></summary>

```bash
pip install llama-cpp-python --force-reinstall --no-cache-dir
```
CPU-only. Works but slower than Apple Silicon.
</details>

<details>
<summary><strong>Linux — NVIDIA GPU (CUDA)</strong></summary>

Requires CUDA Toolkit installed (`nvidia-smi` should work).

```bash
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```
</details>

<details>
<summary><strong>Linux — AMD GPU (Vulkan)</strong></summary>

Requires Vulkan SDK installed.

```bash
CMAKE_ARGS="-DGGML_VULKAN=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```
</details>

<details>
<summary><strong>Linux / macOS — CPU Only</strong></summary>

```bash
pip install llama-cpp-python --force-reinstall --no-cache-dir
```
</details>

<details>
<summary><strong>Windows — NVIDIA GPU (CUDA)</strong></summary>

From PowerShell (requires Visual Studio Build Tools + CUDA Toolkit):

```powershell
$env:CMAKE_ARGS="-DGGML_CUDA=on"
pip install llama-cpp-python --force-reinstall --no-cache-dir
```
</details>

<details>
<summary><strong>Windows — CPU Only</strong></summary>

```powershell
pip install llama-cpp-python --force-reinstall --no-cache-dir
```
</details>

> **Tip:** Run `python setup_model.py --help` to see the recommended command for your detected platform.

### Step 4 — Download the Model

```bash
python setup_model.py
```

Downloads **Qwen3-8B-Q5_K_M** (~5.5 GB) from Hugging Face. One-time download.

> If rate-limited, set a Hugging Face token:
> ```bash
> export HF_TOKEN=your_token    # macOS/Linux
> $env:HF_TOKEN="your_token"    # Windows PowerShell
> python setup_model.py
> ```

### Step 5 — Launch

```bash
python server.py
```

Open **http://localhost:8501** in your browser. The app auto-detects your hardware:

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
╚══════════════════════════════════════════════════╝
```

> ✅ **You're all set!** No API keys. No cloud accounts. No environment variables. Just launch and go.

---

## 🤖 10 Specialist Agents

| Agent | Icon | Expertise |
|-------|------|-----------|
| **Stock Market Analyst** | 📈 | NSE/BSE stocks, Nifty 50/Sensex, sectoral indices, fundamental analysis |
| **Mutual Fund Advisor** | 📊 | SEBI categories, SIP planning, ELSS, direct vs regular, fund comparison |
| **Portfolio Manager** | 💼 | Asset allocation, diversification, SGB, REITs, risk profiling |
| **Tax Advisor** | 🏛️ | New vs Old regime (FY 2025-26), 80C/80D, LTCG/STCG, CTC breakdown, HRA |
| **Retirement Planner** | 🏖️ | EPF, PPF, NPS, SIP, FIRE (5 types), corpus estimation |
| **Loan & EMI Advisor** | 🏠 | Home loan EMI, prepayment analysis, PMAY, CIBIL, RBI repo rate |
| **Budget Planner** | 💰 | 50/30/20 budgeting in ₹, emergency fund, savings rate analysis |
| **Crypto Analyst** | ₿ | Live prices, India crypto tax (30% flat + 1% TDS), exchange comparison |
| **Insurance Advisor** | 🛡️ | Term life, health insurance, IRDAI plans, claim settlement ratios |
| **General Advisor** | 🧠 | Catch-all financial guidance with web search |

Queries are **autonomously routed** by the LLM to the best agent(s) based on intent analysis and an agent dependency graph. Multi-agent queries (e.g., "Should I prepay my home loan or invest in mutual funds?") route to multiple agents, and complex queries trigger automatic self-reflection to ensure comprehensive coverage.

---

## 🧮 36 Financial Calculators

All calculators are accessible via the UI (grid view with search) and API (`POST /api/calculate`).
Formulas are cross-referenced against Groww, ClearTax, ET Money, India Post, and 1% Club.

### Investment & Savings
| Calculator | Key Features |
|-----------|-------------|
| **SIP Calculator** | Year-wise milestones, delay cost (1/3/5yr), wealth multiplier |
| **Lumpsum Calculator** | Doubling time (Rule of 72), real return after inflation, delay cost |
| **Step-Up SIP** | Annual increment, flat vs step-up comparison, advantage % |
| **Goal-Based SIP** | Reverse SIP — monthly amount needed to reach target corpus |
| **Lumpsum vs SIP** | Side-by-side comparison with verdict |
| **Mutual Fund Returns** | SIP/lumpsum modes with expense ratio impact |
| **Compound Interest** | Monthly/quarterly/annual compounding with effective rate |
| **Simple Interest** | Basic SI calculator |
| **XIRR Calculator** | Annualized return for SIP/irregular cashflows |

### Government Schemes
| Calculator | Key Features |
|-----------|-------------|
| **PPF** | 15-year maturity, 80C benefit, PPF advantage over taxable FD, partial withdrawal rules |
| **SSY (Sukanya Samriddhi)** | Girl child scheme, 21-year maturity, wealth multiplier, partial withdrawal age |
| **EPF** | Employer/employee split, salary hike projection, estimated monthly pension |
| **NPS** | Corpus at 60, annuity split, tax savings (80CCD), monthly pension estimate |
| **NSC** | 5-year lock-in, compound interest, 80C deduction |
| **SCSS** | Senior citizen quarterly payout, 8.2% rate |
| **Post Office MIS** | Monthly income scheme, guaranteed returns |
| **APY** | Atal Pension Yojana, ₹1K-5K/month after 60 |
| **KVP** | Kisan Vikas Patra, months to double |

### Fixed Income
| Calculator | Key Features |
|-----------|-------------|
| **FD Calculator** | Quarterly compounding, post-tax maturity, TDS impact, real return, compounding benefit |
| **RD Calculator** | Monthly deposit, wealth multiplier, SIP comparison, SIP advantage over RD |

### Loans
| Calculator | Key Features |
|-----------|-------------|
| **EMI Calculator** | Year-wise amortization, processing fee estimate, affordability check (40% rule) |
| **Education Loan** | Moratorium period, Section 80E benefit, effective rate after tax, min income for EMI |
| **Loan Prepayment** | Reduce tenure vs reduce EMI, interest saved, months saved |
| **Flat vs Reducing Rate** | EMI comparison between flat and reducing balance |

### Tax
| Calculator | Key Features |
|-----------|-------------|
| **Income Tax** | New vs Old regime comparison (FY 2025-26), rebate 87A, slab breakdown |
| **CTC to Take-Home** | Full salary breakdown: Basic, HRA, EPF, gratuity, both regime take-home |
| **Capital Gains Tax** | STCG/LTCG for equity, debt MF, property, gold, crypto; holding optimization tip |
| **HRA Exemption** | 3-way minimum rule, optimal rent suggestion, tax saving estimate |
| **GST Calculator** | Inclusive/exclusive, CGST/SGST split |
| **TDS Calculator** | 8 income types, PAN/no-PAN rates |
| **Gratuity** | Payment of Gratuity Act formula, tax-free limit, net after tax, projections (5-30yr) |

### Planning
| Calculator | Key Features |
|-----------|-------------|
| **Retirement Planner** | Corpus needed, SIP required, step-up SIP option, emergency buffer (6/12 months), wealth multiplier |
| **FIRE Calculator** | 5 FIRE types (Lean/Regular/Fat/Barista/Coast), years to reach each, SIP needed |
| **Inflation Goal Planner** | Future cost with inflation, SIP at 10/12/14%, lumpsum needed today |
| **Salary Hike Analyzer** | Take-home impact at 10/15/20/30% hike with effective hike % |
| **SWP Calculator** | Systematic withdrawal, corpus sustainability, max sustainable monthly withdrawal |

---

## 🏗️ Architecture

### Agentic Design Philosophy

FinanceGPT implements a **hybrid agentic architecture** — combining autonomous LLM decision-making with deterministic financial computation. This is a deliberate design choice: financial calculations must be **exact and reproducible** (SIP of ₹10K/month at 12% for 20 years = ₹99,91,479, every time), while the reasoning layer around them benefits from adaptive intelligence.

**Why not fully autonomous agents?** In finance, a fully autonomous agent (ReAct-style) might decide to skip a tax calculation it deems "unnecessary," or compute SIP differently each time. That's dangerous when users make investment decisions based on the output. FinanceGPT separates **what to compute** (agentic, LLM-driven) from **how to compute** (deterministic, formula-verified), giving you the intelligence of an agent with the reliability of a calculator.

### LangGraph Pipeline with Conditional Edges

```
User Query
    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│  LangGraph Agentic Pipeline (SQLite Checkpointing)                     │
│                                                                        │
│  START → route ─→ gather_context ─→ build_prompt ─→ generate           │
│           ↓              ↓                              ↓              │
│     LLM classifies   Adaptive                  ┌── simple/moderate ─→ END
│     agents +         tool selection:            │                       │
│     complexity +     • simple: calcs only       └── complex ──┐        │
│     search queries   • moderate: + web search                 ↓        │
│                      • complex: + deep research          reflect       │
│                                                              ↓         │
│                                                    ┌── pass ────→ END  │
│                                                    └── fail ──┐        │
│                                                               ↓        │
│                                                           refine → END │
└──────────────────────────────────────────────────────────────────────────┘
    ↓
  FastAPI SSE → Browser
```

### Agentic Capabilities

| Capability | How It Works |
|-----------|--------------|
| **Autonomous Agent Selection** | LLM analyzes query intent and selects 1-3 specialist agents from 10 available, using an agent dependency graph that models inter-relationships, calculators, and context needs |
| **Query Complexity Classification** | LLM classifies each query as `simple`, `moderate`, or `complex` — determining the pipeline path, tool invocation depth, and whether reflection is needed |
| **Adaptive Tool Selection** | Simple queries (greetings, pure calculations) skip web search entirely; moderate queries get standard context; complex queries get deeper research with higher limits |
| **LLM-Generated Search Queries** | The router generates tailored web search queries based on the selected agents' context needs — not generic keywords, but targeted information retrieval |
| **Self-Reflection Loop** | Complex queries trigger a post-generation quality check: a lightweight LLM evaluates whether all aspects of the query were addressed |
| **Automatic Refinement** | If reflection detects gaps (e.g., "no comparison between old and new tax regime as asked"), the LLM generates an improved response incorporating the feedback |
| **Conditional Graph Edges** | The pipeline uses `add_conditional_edges()` — after generation, the graph dynamically routes to reflection, refinement, or directly to END based on query complexity and response quality |
| **Agent Dependency Graph** | 10 agents with explicit `depends_on`, `calculators`, and `context_needs` — enabling intelligent routing that understands which agents handle connected topics |
| **Session Memory** | Profile facts (income, age, risk appetite, goals) are extracted from conversations and persist across sessions via SQLite checkpointing |

### Deterministic Financial Engine

The agentic layer decides **what** to compute; the financial engine guarantees **accuracy**:

| Component | Role | Why Deterministic? |
|-----------|------|-------------------|
| **36 Calculators** | SIP, EMI, FD, PPF, NPS, FIRE, CTC, tax — all verified | Financial math must be exact: ₹1 difference in a 20-year projection = wrong advice |
| **Smart Dispatcher** | Auto-detects computation needs from natural language | Regex-based extraction ensures every number in the query gets processed |
| **Pre-computed Context** | Calculators run before LLM generates response | LLM cites pre-computed ₹ values — never hallucinates numbers |
| **Cross-Referencing** | 53 test cases verified against Groww, ClearTax, ET Money, India Post | Production financial platforms as ground truth |

---

## ⚡ Performance Optimizations

### Caching Stack

| Layer | Mechanism | Scope | TTL | Max Size |
|-------|-----------|-------|-----|----------|
| **KV Cache** | Q8_0 quantized K/V tensors in Llama | Model inference | Session | n_ctx tokens |
| **Prompt Prefix** | Automatic via singleton — reuses KV when prefix matches | Model inference | Until prompt changes | n_ctx tokens |
| **Flash Attention** | `flash_attn=True` in Llama constructor | Prompt prefill | N/A | N/A |
| **Response Cache** | SHA-256 hash of messages → LRU | `generate()` only | 10 min | 64 entries |
| **Calculator Cache** | MD5 hash of (calc_id + inputs) → LRU | `run_calculator()` | 5 min | 256 entries |

### Cache Monitoring

Cache stats are exposed via the health endpoint:

```bash
curl http://localhost:8501/api/health
```

```json
{
  "status": "ok",
  "llm_loaded": true,
  "agents": 10,
  "cache": {
    "response_cache_size": 12,
    "response_cache_hits": 45,
    "response_cache_misses": 67,
    "calculator_cache_size": 8
  }
}
```

### Auto-Scaling Rules

| RAM | Context Window | Max Output | GPU Layers |
|-----|---------------|------------|------------|
| 32 GB+ | 32,768 tokens | 4,096 | All (-1) |
| 16-32 GB | 24,576 tokens | 4,096 | All (-1) |
| 10-16 GB | 16,384 tokens | 2,048 | All (-1) |
| < 10 GB | 8,192 tokens | 2,048 | Auto (partial) |

### Model Quantization

The app uses **Q5_K_M** quantization — the optimal balance for consumer hardware:

| Quant | Size | Quality | Speed | Recommendation |
|-------|------|---------|-------|----------------|
| Q8_0 | ~8.5 GB | Near-lossless | Slower | Best quality, 32 GB+ RAM only |
| **Q5_K_M** | **~5.5 GB** | **Excellent** | **Good** | **Default — best for 16-18 GB RAM** |
| Q4_K_M | ~4.5 GB | Good | Faster | Low-RAM fallback (8-12 GB) |
| Q3_K_M | ~3.5 GB | Degraded | Fastest | Not recommended for financial advice |

---

## 🧰 Tools & Data Sources

| Tool | Source | API Key? | Description |
|------|--------|----------|-------------|
| **Market Data** | yfinance | No | Real-time stock prices, indices, gold, silver, crypto, forex |
| **Web Search** | DuckDuckGo | No | Text + news search, world market briefing |
| **Deep Research** | DuckDuckGo + page fetch | No | Multi-source research with `[1]` citation cards |
| **Smart Calculator** | Internal | N/A | Auto-detects computation needs from natural language |
| **Knowledge Base** | Internal | N/A | Indian finance reference (tax slabs, 80C limits, EPF rates) |
| **File Parser** | PyMuPDF/openpyxl | N/A | CSV, PDF, Excel, JSON, TXT upload and parsing |

---

## 🎨 UI Features

| Feature | Description |
|---------|-------------|
| **Streaming responses** | Token-by-token streaming via SSE with animated cursor |
| **36-calculator grid** | Searchable grid, input forms, instant results with rich formatting |
| **Syntax highlighting** | Code blocks highlighted via highlight.js |
| **Math rendering** | Financial formulas rendered via KaTeX |
| **Light / Dark theme** | Toggle with localStorage persistence |
| **Stop generation** | Click ■ or press `Esc` to stop mid-response |
| **Regenerate** | 🔄 button re-runs the last query |
| **Response feedback** | 👍/👎 buttons on every response |
| **Follow-up suggestions** | 3 context-aware clickable follow-up chips per response |
| **Citation cards** | Perplexity-style `[1]` badges with source domain tooltip |
| **Export conversation** | 📥 Download full chat as Markdown file |
| **File upload** | 📎 Upload CSV/PDF/Excel/JSON for analysis |
| **Pipeline timing** | ⏱ Click time badge to see per-step breakdown |
| **Keyboard shortcuts** | `Esc` stop, `/` focus input, `Cmd+Shift+N` new chat, `Cmd+Shift+E` export |
| **XSS protection** | All LLM output sanitized via DOMPurify before rendering |

---

## 📁 Project Structure

```
financial_advisor/
├── server.py                   # FastAPI backend + SSE streaming (main entry point)
├── app.py                      # Streamlit UI (alternative frontend)
├── config.py                   # Model config, agents, Indian market defaults
├── platform_setup.py           # Cross-platform OS/GPU/RAM auto-detection
├── setup_model.py              # Model downloader + platform install guide
├── requirements.txt            # Python dependencies
├── test_cross_ref.py           # 53 calculator accuracy tests (Groww/ClearTax verified)
│
├── graph/
│   └── workflow.py             # LangGraph agentic pipeline (conditional edges, reflection, refinement)
│
├── llm/
│   └── engine.py               # LLM engine — KV Q8 cache, flash attn, response cache
│
├── agents/
│   ├── base.py                 # Base agent class with auto market data + web search
│   ├── router.py               # LLM-based query router with complexity classification & agent graph
│   ├── stock_analyst.py        # NSE/BSE stock analysis + fundamentals
│   ├── mutual_fund_advisor.py  # Indian mutual fund recommendations
│   ├── portfolio_manager.py    # Portfolio allocation + rebalancing
│   ├── tax_advisor.py          # Indian income tax (new/old regime, CTC, HRA)
│   ├── retirement_planner.py   # SIP, PPF, NPS, FIRE planning
│   ├── loan_advisor.py         # EMI, home loan, PMAY, prepayment
│   ├── budget_planner.py       # Budget in ₹ with savings plan
│   ├── crypto_analyst.py       # Crypto + India 30% tax rules
│   ├── insurance_advisor.py    # IRDAI term + health insurance
│   └── general_advisor.py      # General financial guidance
│
├── tools/
│   ├── market_data.py          # yfinance: stocks, indices, crypto, forex, gold
│   ├── financial_calc.py       # 36 calculators (2500+ lines, cross-referenced)
│   ├── calculator_registry.py  # Calculator definitions, validation, result caching
│   ├── smart_calc.py           # Auto-dispatch: detects computation needs from query
│   ├── deep_research.py        # Multi-source web research with citations
│   ├── web_search.py           # DuckDuckGo search + world briefing (thread-safe)
│   └── file_parser.py          # CSV/PDF/Excel/JSON/TXT file parser
│
├── knowledge/
│   └── indian_finance.py       # Indian finance reference data (tax slabs, 80C, etc.)
│
├── static/
│   ├── index.html              # Full UI — chat, calculators, themes, streaming
│   └── style.css               # Streamlit custom styles (app.py frontend)
│
├── models/                     # Downloaded .gguf model (~5.5 GB, auto-downloaded)
├── sessions/
│   └── checkpoints.db          # LangGraph SQLite checkpoint (auto-created)
└── logs/
    └── financegpt.log          # Application logs
```

---

## 🔌 API Reference

### Chat (SSE Streaming)

```bash
curl -X POST http://localhost:8501/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "SIP of ₹10K/month for 20 years at 12%", "agent": "auto"}'
```

SSE events: `session`, `status`, `agent`, `token`, `done`, `error`

### Calculator

```bash
curl -X POST http://localhost:8501/api/calculate \
  -H "Content-Type: application/json" \
  -d '{"calculator": "sip", "inputs": {"monthly_investment": "10000", "annual_rate": "12", "years": "20"}}'
```

### All Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main UI (serves index.html) |
| `GET` | `/api/agents` | List all available agents |
| `GET` | `/api/calculators` | List all 36 calculators with field definitions |
| `POST` | `/api/calculate` | Run a calculator with inputs |
| `POST` | `/api/chat` | Chat with SSE streaming |
| `POST` | `/api/upload` | Upload file for analysis |
| `DELETE` | `/api/upload/{session_id}` | Clear uploaded files |
| `DELETE` | `/api/session/{session_id}` | Clear conversation history |
| `GET` | `/api/health` | Health check with cache stats |

---

## ⚙️ Configuration

### Auto-Detected Settings

The app runs `platform_setup.py` at import time — no manual config needed:

| Detection | What It Does |
|-----------|-------------|
| **OS & Architecture** | Detects macOS/Linux/Windows and arm64/x86_64 |
| **GPU** | Tests Metal → CUDA → Vulkan → CPU fallback |
| **RAM** | Reads total system memory, scales context window |
| **CPU cores** | Uses ~70% of cores for inference threads |

### Manual Overrides (config.py)

Override any auto-detected value:

```python
LLM_CONFIG["n_ctx"] = 16384        # Force smaller context window
LLM_CONFIG["n_gpu_layers"] = 0     # Force CPU-only mode
LLM_CONFIG["n_threads"] = 4        # Limit threads
LLM_CONFIG["max_tokens"] = 2048    # Shorter responses
LLM_CONFIG["temperature"] = 0.7    # Creativity (0.0 = deterministic)
```

---

## 💬 Example Queries

**Stocks & Markets**
- "Analyze Reliance Industries stock — fundamentals and outlook"
- "Compare TCS vs Infosys vs Wipro"
- "What's happening with Nifty 50 and Bank Nifty today?"

**Mutual Funds**
- "Best ELSS funds for tax saving under 80C"
- "SIP of ₹10,000/month for 20 years at 12%"
- "Compare Parag Parikh Flexi Cap vs HDFC Flexi Cap"

**Tax Planning**
- "New vs old tax regime for ₹15 lakh salary"
- "CTC ₹24 LPA — calculate take-home salary"
- "Capital gains tax on selling ₹5L of shares after 2 years"

**Loans & Insurance**
- "EMI for ₹50 lakh home loan at 8.5% for 20 years"
- "Should I prepay my loan or invest in mutual funds?"
- "Best term insurance plans for a 30-year-old"

**Budget & Retirement**
- "Budget for ₹1 lakh monthly salary"
- "How much corpus to retire at 50 with ₹60K/month expenses?"
- "I'm 28, can I reach ₹5 crore by 55?"

**FIRE Planning**
- "Monthly expenses ₹50K, age 30 — show Lean/Regular/Fat/Barista/Coast FIRE numbers"
- "How much SIP do I need for Regular FIRE by 50?"

---

## ✅ Testing & Accuracy

### Cross-Reference Test Suite

All 36 calculators are verified against production financial platforms:

```bash
python test_cross_ref.py
```

```
53/53 cross-reference checks passed
```

| Source | What's Verified |
|--------|----------------|
| **Groww** | SIP, Lumpsum, EMI, FD, RD, PPF, SSY, EPF, Gratuity, GST, SWP |
| **ClearTax** | SIP (3 scenarios), EMI (2 scenarios), PPF |
| **ET Money** | FIRE calculator (Barista FIRE methodology) |
| **1% Club** | FIRE calculator (Regular/Lean/Fat multipliers) |
| **India Post** | KVP, SCSS, POMIS rates |
| **IT Act FY25-26** | Tax brackets, rebate 87A, capital gains rates |

---

## 🔒 Privacy & Security

- **100% local LLM** — model runs entirely on your machine via llama-cpp-python
- **No API keys needed** — DuckDuckGo search, yfinance market data are keyless
- **No telemetry** — zero tracking, zero analytics, zero cloud calls
- **No data leaves your PC** — works fully offline (except web search and market data)
- **XSS protection** — all LLM output sanitized via DOMPurify before rendering
- **Input validation** — all calculator inputs validated with type, min/max, and required checks
- **No secrets in code** — no hardcoded tokens, keys, or credentials

---

## 🔄 Deploying on Another Machine

```bash
# 1. Copy the project (excluding large/generated files)
rsync -av --exclude='models/' --exclude='sessions/' --exclude='logs/' \
  --exclude='uploads/' --exclude='__pycache__/' --exclude='venv/' \
  financial_advisor/ user@host:~/financial_advisor/

# 2. On the target machine
cd ~/financial_advisor
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Install llama-cpp-python (platform-specific — see Step 3 above)
python setup_model.py --help    # shows the right command for your OS

# 4. Download the model (~5.5 GB one-time)
python setup_model.py

# 5. Launch
python server.py
# Open http://localhost:8501
```

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| **Model download fails** | Set `export HF_TOKEN=your_token` and retry `python setup_model.py` |
| **Slow responses** | Check GPU detection in startup log. Ensure Metal/CUDA is compiled in llama-cpp-python |
| **Out of memory** | Reduce context: `LLM_CONFIG["n_ctx"] = 16384` in config.py. Or use partial GPU offload: `LLM_CONFIG["n_gpu_layers"] = 20` |
| **Port 8501 in use** | `kill $(lsof -ti:8501)` on macOS/Linux. `netstat -ano \| findstr :8501` on Windows |
| **`ModuleNotFoundError`** | Activate venv: `source venv/bin/activate` then `pip install -r requirements.txt` |
| **No GPU detected** | The app falls back to CPU automatically. Verify GPU: `nvidia-smi` (CUDA) or `system_profiler SPDisplaysDataType` (macOS) |
| **Windows cmake errors** | Install Visual Studio Build Tools + CMake. Try the pre-built wheel from [llama-cpp-python releases](https://github.com/abetlen/llama-cpp-python/releases) |
| **Market data not loading** | Requires internet connection. Check firewall/proxy settings |
| **Flash attention warning** | Safe to ignore if your llama-cpp-python build doesn't support it — falls back gracefully |
| **Calculator tests fail** | Run `python test_cross_ref.py` — should be 53/53. If not, check recent changes to `financial_calc.py` |

---

## 📊 Performance Benchmarks

Every response includes a clickable ⏱ timing badge:

| Metric | Description |
|--------|-------------|
| **Routing** | Time to classify query and select agent(s) |
| **Context Gathering** | Web search + market data + deep research (parallel) |
| **Prompt Build** | System prompt assembly + token budget trimming |
| **TTFT** | Time to first token from LLM |
| **Inference** | Total LLM generation time |
| **Tokens/sec** | Generation throughput |
| **Total** | End-to-end wall-clock time |

Typical performance on Apple M3 Pro (18 GB):
- **TTFT:** 1-3 seconds (depends on prompt length)
- **Generation:** 15-25 tokens/sec
- **Calculator:** <0.1ms (cached), <1ms (computed)

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `llama-cpp-python` | Local LLM inference with Metal/CUDA/CPU |
| `huggingface-hub` | Model download from Hugging Face |
| `fastapi` + `uvicorn` | HTTP server + SSE streaming |
| `langgraph` | Declarative state graph pipeline |
| `langgraph-checkpoint-sqlite` | Session persistence via SQLite |
| `yfinance` | Real-time market data (NSE/BSE/crypto/forex) |
| `duckduckgo-search` | Web search and news (no API key) |
| `numpy` + `numpy-financial` | Financial math (NPV, IRR, PMT, FV) |
| `pandas` | Data manipulation for market data |
| `beautifulsoup4` | HTML parsing for deep research |
| `PyMuPDF` + `pdfplumber` | PDF parsing for file uploads |
| `openpyxl` + `xlrd` | Excel file parsing |

---

## 📄 License

This project is for personal use. The Qwen3 model is released under the [Apache 2.0 License](https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE).

---

*Built with ❤️ for Indian investors. Powered by Qwen3-8B + llama-cpp-python + LangGraph + FastAPI. Agentic architecture with deterministic financial accuracy.*
