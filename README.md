# 💹 FinanceGPT — AI Personal Financial Advisor

A **100% local, privacy-first** AI financial advisor powered by **Qwen3-8B** (via llama-cpp-python) and **LangGraph**, tailored for the **Indian market**. Runs on **macOS, Linux, and Windows** with automatic CPU/GPU detection.

All processing happens on your machine — your financial data never leaves your computer.

---

## ✨ Key Highlights

- **Cross-platform** — macOS (Apple Silicon + Intel), Linux, Windows
- **Auto GPU detection** — Metal (Mac), CUDA (NVIDIA), Vulkan (AMD), CPU fallback
- **10 specialist AI agents** — stocks, MF, tax, retirement, loans, budget, crypto, insurance, portfolio, general
- **LangGraph pipeline** — declarative state graph with SQLite checkpointing
- **Real-time data** — yfinance market data + DuckDuckGo web search (no API keys)
- **Deep research** — multi-source web research with Perplexity-style citations
- **14+ financial calculators** — EMI, SIP, CAGR, NPV, IRR, tax brackets, and more
- **Smart Calculator Dispatcher** — auto-detects when a query needs computation and pre-computes ₹ values
- **Modern UI** — streaming responses, syntax highlighting, math rendering (KaTeX), light/dark themes
- **Session persistence** — conversation history and user profile survive restarts
- **Pipeline timing** — per-step performance breakdown for every query

---

## 🖥️ System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 8 GB | 16 GB+ |
| **Disk** | 8 GB free | 12 GB free |
| **CPU** | Any 64-bit | Apple Silicon / modern x86 |
| **GPU** | Not required | Apple Metal / NVIDIA CUDA / AMD Vulkan |
| **OS** | macOS 12+, Ubuntu 20.04+, Windows 10+ | macOS (Apple Silicon) |
| **Python** | 3.10+ | 3.11+ |

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repo-url>
cd financial_advisor
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install llama-cpp-python (Platform-Specific)

The setup script auto-detects your platform and shows the right command:

```bash
python setup_model.py --help
```

Or install manually:

<details>
<summary><strong>macOS — Apple Silicon (M1/M2/M3/M4)</strong></summary>

```bash
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```
</details>

<details>
<summary><strong>macOS — Intel</strong></summary>

```bash
pip install llama-cpp-python --force-reinstall --no-cache-dir
```
</details>

<details>
<summary><strong>Linux — NVIDIA GPU (CUDA)</strong></summary>

Requires CUDA toolkit installed.

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

From PowerShell (requires Visual Studio build tools + CUDA toolkit):

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

### 5. Download the Model

```bash
python setup_model.py
```

Downloads **Qwen3-8B-Q5_K_M** (~5.5 GB) from Hugging Face. One-time download.

> **Tip:** If you get rate-limited, set a Hugging Face token:
> ```bash
> export HF_TOKEN=your_token    # macOS/Linux
> $env:HF_TOKEN="your_token"    # Windows PowerShell
> python setup_model.py
> ```

### 6. Launch

```bash
python server.py
```

Open **http://localhost:8501** — the app auto-detects your hardware and logs it:

```
╔══════════════════════════════════════════════════╗
║          FinanceGPT — System Detection           ║
╠══════════════════════════════════════════════════╣
║  OS          : Darwin (arm64)                    ║
║  RAM         : 18,432 MB (18 GB)                 ║
║  CPU Threads : 8                                 ║
║  GPU Backend : METAL                             ║
║  GPU Name    : Apple M3 Pro                      ║
║  GPU VRAM    : 13,824 MB                         ║
║  GPU Layers  : -1 (-1 = all)                     ║
╠══════════════════════════════════════════════════╣
║  Context     : 24,576 tokens                     ║
║  Max Output  : 4,096 tokens                      ║
║  Threads     : 8                                 ║
╚══════════════════════════════════════════════════╝
```

---

## 🤖 Specialist Agents

| Agent | Icon | Expertise |
|-------|------|-----------|
| **Stock Market Analyst** | 📈 | NSE/BSE stocks, Nifty 50/Sensex, sectoral indices, fundamental analysis (Graham/PEG/DDM) |
| **Mutual Fund Advisor** | 📊 | SEBI categories, SIP planning, ELSS, direct vs regular plans, fund comparison |
| **Portfolio Manager** | 💼 | Asset allocation, diversification, SGB, REITs, risk profiling |
| **Tax Advisor** | 🏛️ | New vs Old regime, 80C/80D deductions, LTCG/STCG, CTC breakdown, HRA |
| **Retirement Planner** | 🏖️ | EPF, PPF, NPS, SIP calculator, FIRE planning, corpus estimation |
| **Loan & EMI Advisor** | 🏠 | Home loan EMI, PMAY, CIBIL, RBI repo rate, prepayment analysis |
| **Budget Planner** | 💰 | 50/30/20 budgeting in ₹, emergency fund, savings rate |
| **Crypto Analyst** | ₿ | Live prices, India crypto tax (30% + 1% TDS), exchange comparison |
| **Insurance Advisor** | 🛡️ | Term life, health insurance, IRDAI plans, claim settlement ratios |
| **General Advisor** | 🧠 | Catch-all financial guidance with web search |

Queries are **automatically routed** to the best agent(s). Multi-agent queries (e.g., "Should I prepay my home loan or invest in mutual funds?") route to multiple agents and produce a unified response.

---

## 🧰 Built-in Tools

| Tool | Description |
|------|-------------|
| **Market Data** | Real-time stock prices, indices, sectors, gold/silver via yfinance |
| **Financial Calculators** | EMI, SIP, CAGR, NPV, IRR, FD maturity, PPF, HRA, tax brackets (India & US) |
| **Smart Calculator** | Auto-detects computation needs and pre-computes ₹ values fed to the LLM |
| **Web Search** | DuckDuckGo text + news search (no API key), world market briefing |
| **Deep Research** | Multi-source web research with page fetching and Perplexity-style citations |
| **File Parser** | Upload CSV, PDF, Excel, JSON, TXT — content injected into context |
| **Knowledge Base** | Indian finance reference data (tax slabs, 80C limits, NPS rules, etc.) |

---

## 🎨 UI Features

| Feature | Description |
|---------|-------------|
| **Streaming responses** | Token-by-token streaming with animated cursor |
| **Syntax highlighting** | Code blocks highlighted via highlight.js |
| **Math rendering** | Financial formulas rendered via KaTeX |
| **Light / Dark theme** | Toggle with persistence (keyboard: theme button in sidebar) |
| **Stop generation** | Click ■ or press `Esc` to stop mid-response |
| **Regenerate** | 🔄 button re-runs the last query |
| **Response feedback** | 👍/👎 buttons on every response |
| **Follow-up suggestions** | 3 context-aware clickable follow-up chips per response |
| **Citation cards** | Perplexity-style `[1]` badges with source domain tooltip |
| **Export conversation** | 📥 Download full chat as Markdown file |
| **File upload** | 📎 Upload CSV/PDF/Excel/JSON for analysis |
| **Pipeline timing** | ⏱ Click time badge to see per-step breakdown |
| **Keyboard shortcuts** | `Esc` stop, `/` focus input, `Cmd+Shift+N` new chat, `Cmd+Shift+E` export |

---

## 🏗️ Architecture

```
START → route → gather_context → build_prompt → stream_llm → END
```

- **LangGraph StateGraph** — declarative pipeline with SQLite checkpointing
- **Parallel context gathering** — market data, web search, deep research, and agent context all run concurrently (ThreadPoolExecutor)
- **Smart routing** — LLM-based classifier with embedded agent relationship graph for multi-agent co-selection
- **Token budget management** — auto-trims context to fit within n_ctx
- **User profile extraction** — financial facts (income, age, EMI, goals) automatically extracted and persisted across exchanges

---

## 📁 Project Structure

```
financial_advisor/
├── server.py                   # FastAPI backend + SSE streaming (entry point)
├── config.py                   # Model config, agents, Indian market defaults
├── platform_setup.py           # Cross-platform OS/GPU/RAM auto-detection
├── setup_model.py              # Model downloader + platform install guide
├── requirements.txt            # Python dependencies
│
├── graph/
│   └── workflow.py             # LangGraph pipeline (route → context → prompt → stream)
│
├── llm/
│   └── engine.py               # LLM engine (llama-cpp-python, Metal/CUDA/CPU)
│
├── agents/
│   ├── base.py                 # Base agent class with auto market data + web search
│   ├── router.py               # LLM-based query router with agent relationship graph
│   ├── stock_analyst.py        # NSE/BSE stock analysis + fundamentals
│   ├── mutual_fund_advisor.py  # Indian mutual fund recommendations
│   ├── portfolio_manager.py    # Portfolio allocation + rebalancing
│   ├── tax_advisor.py          # Indian income tax (new/old regime, CTC)
│   ├── retirement_planner.py   # SIP, PPF, NPS, FIRE planning
│   ├── loan_advisor.py         # EMI, home loan, PMAY, prepayment
│   ├── budget_planner.py       # Budget in ₹ with savings plan
│   ├── crypto_analyst.py       # Crypto + India 30% tax rules
│   ├── insurance_advisor.py    # IRDAI term + health insurance
│   └── general_advisor.py      # General financial guidance
│
├── tools/
│   ├── market_data.py          # yfinance: stocks, indices, crypto, forex, gold
│   ├── financial_calc.py       # 14+ calculators (EMI, SIP, tax, CAGR, NPV, IRR)
│   ├── smart_calc.py           # Auto-dispatch: detects computation needs from query
│   ├── deep_research.py        # Multi-source web research with citations
│   ├── web_search.py           # DuckDuckGo search + world briefing (thread-safe)
│   └── file_parser.py          # CSV/PDF/Excel/JSON/TXT file parser
│
├── knowledge/
│   └── indian_finance.py       # Indian finance reference data (tax slabs, 80C, etc.)
│
├── static/
│   └── index.html              # Full UI (HTML/CSS/JS) — chat, themes, streaming
│
├── models/                     # Downloaded .gguf model (~5.5 GB)
└── sessions/
    └── checkpoints.db          # LangGraph SQLite checkpoint (auto-created)
```

---

## ⚙️ Configuration

### Auto-Detected Settings

The app automatically detects your hardware at startup via `platform_setup.py`:

| Detection | What It Does |
|-----------|-------------|
| **OS & Architecture** | Detects macOS/Linux/Windows and arm64/x86_64 |
| **GPU** | Tests Metal → CUDA → Vulkan → CPU fallback |
| **RAM** | Reads total system memory, scales context window |
| **CPU cores** | Uses ~70% of cores for inference threads |

### Manual Overrides (config.py)

Override any auto-detected value in `config.py`:

```python
LLM_CONFIG["n_ctx"] = 16384       # Force smaller context window
LLM_CONFIG["n_gpu_layers"] = 0    # Force CPU-only mode
LLM_CONFIG["n_threads"] = 4       # Limit threads
LLM_CONFIG["max_tokens"] = 2048   # Shorter responses
```

### Auto-Scaling Rules

| RAM | Context Window | Max Output |
|-----|---------------|------------|
| 32 GB+ | 32,768 tokens | 4,096 |
| 16–32 GB | 24,576 tokens | 4,096 |
| 10–16 GB | 16,384 tokens | 2,048 |
| < 10 GB | 8,192 tokens | 2,048 |

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

---

## 🔒 Privacy & Security

- **100% local LLM** — model runs entirely on your machine via llama-cpp-python
- **No API keys needed** — DuckDuckGo search, yfinance market data are keyless
- **No telemetry** — zero tracking, zero analytics, zero cloud calls
- **No data leaves your PC** — works fully offline (except web search and market data)
- **XSS protection** — all LLM output sanitized via DOMPurify before rendering

---

## 🔄 Deploying on Another Machine

```bash
# 1. Copy the project (excluding models/ and sessions/)
rsync -av --exclude='models/' --exclude='sessions/' financial_advisor/ user@host:~/financial_advisor/

# 2. On the target machine
cd ~/financial_advisor
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Install llama-cpp-python (see platform-specific command)
python setup_model.py --help    # shows the right command for your OS

# 4. Download the model
python setup_model.py

# 5. Launch
python server.py
```

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| **Model download fails** | Set `export HF_TOKEN=your_token` (or `$env:HF_TOKEN` on Windows) and retry |
| **Slow responses** | Check GPU detection in startup log. Ensure Metal/CUDA is compiled in llama-cpp-python |
| **Out of memory** | Set `LLM_CONFIG["n_gpu_layers"] = 20` for partial offload, or reduce `n_ctx` |
| **Port 8501 in use** | macOS/Linux: `kill $(lsof -ti:8501)` — Windows: `netstat -ano \| findstr :8501` |
| **`ModuleNotFoundError`** | Activate venv and run `pip install -r requirements.txt` |
| **No GPU detected** | The app falls back to CPU automatically. Check `nvidia-smi` or `system_profiler SPDisplaysDataType` |
| **Windows: cmake errors** | Install Visual Studio Build Tools + CMake. Use the pre-built wheel if available |
| **market data not loading** | Requires internet. Check firewall/proxy settings |

---

## 📊 Performance Benchmarks

Every response includes a clickable ⏱ timing badge that shows:

| Metric | Description |
|--------|-------------|
| **Routing** | Time to classify query and select agent(s) |
| **Context Gathering** | Web search + market data + deep research (parallel) |
| **Prompt Build** | System prompt assembly + token budget trimming |
| **TTFT** | Time to first token from LLM |
| **Inference** | Total LLM generation time |
| **Tokens/sec** | Generation speed |
| **Total** | End-to-end wall-clock time |

---

## 📄 License

This project is for personal use. The Qwen3 model is released under the [Apache 2.0 License](https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE).

---

*Built with ❤️ for Indian investors. Powered by Qwen3-8B + llama-cpp-python + LangGraph + FastAPI.*
