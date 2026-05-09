# Configuration Guide

FinanceGPT auto-detects your hardware and configures itself optimally. This guide explains what's auto-detected and how to override any setting.

---

## Table of Contents

- [Auto-Detection (No Config Needed)](#auto-detection-no-config-needed)
- [Pipeline Tuning (CPU vs GPU)](#pipeline-tuning-cpu-vs-gpu)
- [LLM Settings](#llm-settings)
- [Model Selection](#model-selection)
- [Router Configuration](#router-configuration)
- [Market Data Settings](#market-data-settings)
- [Indian Market Defaults](#indian-market-defaults)
- [Agent Configuration](#agent-configuration)
- [Advanced Overrides](#advanced-overrides)

---

## Auto-Detection (No Config Needed)

When you launch FinanceGPT, `platform_setup.py` runs automatically and detects:

| What | How | Result |
|------|-----|--------|
| OS | `platform.system()` | macOS / Linux / Windows |
| Architecture | `platform.machine()` | arm64 / x86_64 |
| GPU | Metal → CUDA → Vulkan → CPU | Backend + GPU name |
| RAM | `psutil` / system calls | Total MB |
| CPU cores | `os.cpu_count()` | Thread count |

**Based on detection, it auto-computes:**

| Setting | How It's Determined |
|---------|-------------------|
| Context window (`n_ctx`) | RAM-based: 2K–8K (CPU), 8K–32K (GPU) |
| GPU layers (`n_gpu_layers`) | -1 (all) for GPU, 0 for CPU |
| Thread count (`n_threads`) | ~70-80% of CPU cores |
| Batch size (`n_batch`) | 1024 (GPU), 512 (CPU 16GB+), 256 (CPU <16GB) |
| Max output tokens (`max_tokens`) | 2048–4096 (GPU), 1536 (CPU 16GB+), 1024 (CPU <16GB) |
| KV cache type | Q8_0 (GPU), Q4_0 (CPU) |
| Flash attention | On (GPU), Off (CPU) |
| Model file | Q5_K_M (GPU), Q4_K_M (CPU 16GB+), Q3_K_M (CPU <16GB) |
| Memory mapping (`use_mmap`) | Always True (faster load, lower RSS) |
| Memory lock (`use_mlock`) | True (GPU), False (CPU — lets OS page-out) |

**You don't need to change any of this** — it works out of the box.

---

## Pipeline Tuning (CPU vs GPU)

The pipeline depth is automatically adjusted based on your hardware.

### What each setting controls

| Setting | What It Does | CPU <16GB | CPU 16GB+ | GPU |
|---------|-------------|-----------|-----------|-----|
| `ROUTER_MAX_TOKENS` | Max tokens for router classification | 100 | 100 | 150 |
| `RESPONSE_MAX_TOKENS` | Max tokens in AI response | 1,024 | 1,536 | 4,096 |
| `REFLECTION_ENABLED` | Quality check after generation | `False` | `False` | `True` |
| `DEEP_RESEARCH_MAX_CHARS` | Max chars from web research | 2,500 | 3,500 | 7,000 |
| `THINKING_ENABLED` | Internal reasoning for complex queries | `True` | `True` | `True` |
| `THINKING_BUDGET_HINT` | Word budget hint for think block | 40 | 80 | 200 |
| `CONTEXT_BUDGET_RESERVE` | Tokens reserved for overhead | 200 | 200 | 100 |
| `PER_TOKEN_TIMEOUT` | Per-token wait timeout (seconds) | 300 | 300 | 120 |

### Why CPU skips reflection and thinking

On CPU, a full response takes 15-40 seconds. Adding reflection (+10s) and thinking (+15s) would push total time to 40-65 seconds — too slow for interactive use. The lean pipeline keeps the core functionality (agents, calculators, market data, search) while cutting the most time-consuming optional steps.

### Override example

To enable reflection on CPU (if you don't mind longer wait times):

```python
# In config.py, after the CPU/GPU pipeline section:
REFLECTION_ENABLED = True    # Override: enable on CPU too
THINKING_ENABLED = True      # Override: enable thinking on CPU
```

---

## LLM Settings

All LLM inference settings live in `LLM_CONFIG` in config.py.

### Auto-detected settings

| Setting | Description | Typical Value |
|---------|-------------|---------------|
| `n_ctx` | Context window (tokens) | 2048–32768 |
| `n_gpu_layers` | Layers offloaded to GPU | -1 (all) or 0 (CPU) |
| `n_threads` | CPU threads for inference | ~70-80% of cores |
| `n_batch` | Batch size for prompt processing | 512 or 1024 |
| `max_tokens` | Max response length | 1536–4096 |
| `flash_attn` | Flash attention (prefill speedup) | True/False |
| `type_k` / `type_v` | KV cache quantization | Q8_0 or Q4_0 |

### Qwen3-specific settings (tuned for financial advice)

| Setting | Value | Why |
|---------|-------|-----|
| `temperature` | 0.7 | Balanced creativity — not too random, not too deterministic |
| `top_p` | 0.8 | Nucleus sampling threshold |
| `top_k` | 20 | Limits vocabulary per token |
| `repeat_penalty` | 1.15 | Prevents repetitive paragraphs |

### Overriding LLM settings

Edit `config.py`:

```python
# Force smaller context window (saves memory)
LLM_CONFIG["n_ctx"] = 8192

# Force CPU-only mode (even if GPU is available)
LLM_CONFIG["n_gpu_layers"] = 0

# More creative responses
LLM_CONFIG["temperature"] = 0.9

# More deterministic responses (good for calculations)
LLM_CONFIG["temperature"] = 0.3

# Limit threads (useful if running other apps)
LLM_CONFIG["n_threads"] = 4
```

---

## Model Selection

### Auto-selected models

| Hardware | Model File | Size | Quantization |
|----------|-----------|------|-------------|
| GPU (Metal/CUDA/Vulkan) | `Qwen_Qwen3-8B-Q5_K_M.gguf` | ~5.5 GB | Q5_K_M (very good quality) |
| CPU with 16 GB+ RAM | `Qwen_Qwen3-8B-Q4_K_M.gguf` | ~4.6 GB | Q4_K_M (good quality, faster) |
| CPU with <16 GB RAM | `Qwen_Qwen3-8B-Q3_K_M.gguf` | ~3.9 GB | Q3_K_M (good quality, fastest CPU) |

### Using a different quantization

```python
# In config.py:
MODEL_FILE = "Qwen_Qwen3-8B-Q8_0.gguf"   # Highest quality (needs 32GB+ RAM)
# or
MODEL_FILE = "Qwen_Qwen3-8B-Q3_K_M.gguf"  # Fastest CPU inference (auto-selected for <16GB RAM)
```

### Using a different model entirely

```python
# In config.py:
MODEL_REPO = "TheBloke/Some-Other-Model-GGUF"
MODEL_FILE = "some-other-model.Q5_K_M.gguf"
```

Or simply place any GGUF file in the `models/` directory — the engine auto-discovers GGUF files.

### Local model conversion

Place SafeTensors or PyTorch model files in `models/` — the engine auto-converts to GGUF. See [Installation Guide → Air-Gapped](INSTALLATION.md#air-gapped--offline-installation).

---

## Router Configuration

The router decides which specialist agents handle each query.

### Router mode

```python
# In config.py:
ROUTER_MODE = "llm_only"        # LLM classifies every query (most accurate)
# or
ROUTER_MODE = "keyword_first"   # Try keyword matching first, LLM fallback (faster)
```

| Mode | Speed | Accuracy | When to Use |
|------|-------|----------|-------------|
| `llm_only` | ~1-3s | Excellent | Default — best intent understanding |
| `keyword_first` | ~0.1s for keywords, ~1-3s fallback | Good | If router speed is a bottleneck |

### Router cache

The router caches LLM classification results for 5 minutes. Similar questions skip the LLM router entirely. This is enabled by default and not configurable.

---

## Market Data Settings

### Market prefetch

```python
# In config.py:
MARKET_PREFETCH = True     # Background thread pre-fetches market data (recommended)
# or
MARKET_PREFETCH = False    # All market data fetched per-query
```

When enabled, a background thread fetches standard market data (indices, gold, forex) at server startup and refreshes every hour. This eliminates the 1-3 second yfinance delay when queries need market data.

---

## Indian Market Defaults

These are set for the Indian market and affect formatting throughout the app:

```python
# In config.py:
DEFAULT_CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"
DEFAULT_EXCHANGE = "NSE"        # National Stock Exchange of India
INDIAN_NUMBER_SYSTEM = True     # 1 Lakh = 1,00,000 | 1 Crore = 1,00,00,000
```

---

## Agent Configuration

### Available agents

10 specialist agents are defined in `config.py`:

```python
AGENTS = {
    "stock_analyst": "Stock Market Analyst (NSE/BSE)",
    "portfolio_manager": "Portfolio Manager",
    "tax_advisor": "Tax & Compliance Advisor (India)",
    "retirement_planner": "Retirement & SIP Planner",
    "loan_advisor": "Loan & EMI Advisor",
    "budget_planner": "Budget & Savings Planner",
    "crypto_analyst": "Cryptocurrency Analyst",
    "insurance_advisor": "Insurance Advisor (India)",
    "mutual_fund_advisor": "Mutual Fund Advisor",
    "general_advisor": "General Financial Advisor",
}
```

Each agent has:
- A specialized system prompt (in its respective file under `agents/`)
- An icon (defined in `AGENT_ICONS`)
- Context-gathering logic (calculators, market data, web search)

### Disabling an agent

Remove it from the `AGENTS` dict and `AGENT_ICONS` dict in `config.py`. The router will no longer route to it.

---

## Advanced Overrides

### Environment variables

| Variable | Purpose |
|----------|---------|
| `HF_TOKEN` | HuggingFace token for model download (if rate-limited) |
| `FINANCEGPT_CLOUD_API_KEY` | API key for cloud LLM provider (when `USE_CLOUD_LLM=True`) |
| `FINANCEGPT_STARTUP` | Set to `"1"` to print system detection banner (auto-set by server.py) |

### Proxy & Network (Corporate / Air-Gapped)

```python
# In config.py:
PROXY_ENABLED = True
PROXY_URL = "http://proxy.corp.example.com:8080"

# Custom pip index for air-gapped package installs:
PIP_INDEX_URL = "https://nexus.corp.example.com/repository/pypi/simple"
PIP_TRUSTED_HOST = "nexus.corp.example.com"
```

The proxy is applied to all outbound HTTP traffic: yfinance, DuckDuckGo, MFAPI, NSE, Swissquote gold feed, and cloud LLM API calls.

### Cloud LLM Mode

Skip local model loading entirely and use a cloud-hosted LLM via the OpenAI-compatible API:

```python
# In config.py:
USE_CLOUD_LLM = True
CLOUD_LLM = {
    "api_base": "https://api.openai.com/v1",
    "api_key": os.environ.get("FINANCEGPT_CLOUD_API_KEY", ""),
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 2048,
    "timeout": 60,
}
```

Compatible with: OpenAI, Groq, Together AI, Google Gemini, Ollama, LM Studio, vLLM, Azure OpenAI, and any OpenAI-compatible endpoint. See [Installation Guide → Cloud LLM Setup](INSTALLATION.md#cloud-llm-setup) for provider details.

When `USE_CLOUD_LLM=True`, `llama-cpp-python` is not required.

### Memory optimization for low-RAM systems

Most of these are now **auto-applied** for systems with <16 GB RAM (Q3_K_M model, 2K context, 256 batch size). Manual overrides only needed for further tuning:

```python
# In config.py:
LLM_CONFIG["n_ctx"] = 2048             # Minimum context window (auto-set for <16GB)
LLM_CONFIG["n_gpu_layers"] = 0         # Force CPU (no GPU memory used)
RESPONSE_MAX_TOKENS = 1024              # Shorter responses (auto-set for <16GB)
DEEP_RESEARCH_MAX_CHARS = 2000          # Less web context
PER_TOKEN_TIMEOUT = 600                 # Increase if you see timeout errors on slow CPU
```

### Maximum quality for high-end systems

```python
# In config.py:
LLM_CONFIG["n_ctx"] = 32768           # Large context window
MODEL_FILE = "Qwen_Qwen3-8B-Q8_0.gguf"  # Best quantization
RESPONSE_MAX_TOKENS = 4096             # Full-length responses
DEEP_RESEARCH_MAX_CHARS = 10000        # Extended research
REFLECTION_ENABLED = True              # Quality check
THINKING_ENABLED = True                # Visible reasoning
```
