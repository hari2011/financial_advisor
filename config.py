import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

# ──────────────────────── Platform Detection ────────────────────────
# Auto-detects OS, CPU, GPU, RAM and computes optimal settings.
# Import triggers detection once; results are cached.
from platform_setup import (
    SYSTEM, MACHINE, IS_MACOS, IS_LINUX, IS_WINDOWS,
    GPU, TOTAL_RAM_MB, CPU_THREADS, OPTIMAL_CONFIG,
)

# ──────────────────────── Model Configuration ────────────────────────
# Qwen3 8B (April 2025)
# Hybrid thinking/non-thinking model, superior reasoning vs Qwen 2.5
# Standard transformer architecture — fully compatible with llama-cpp-python
#
# Model selection by platform & RAM:
#   GPU (Metal/CUDA/Vulkan)   → Q5_K_M (~5.5 GB) — best quality
#   CPU-only, 16 GB+ RAM      → Q4_K_M (~4.6 GB) — good quality, reasonable speed
#   CPU-only, <16 GB RAM      → Q3_K_M (~3.9 GB) — fastest CPU, still good for financial Q&A
MODEL_REPO = "bartowski/Qwen_Qwen3-8B-GGUF"

IS_CPU_ONLY = GPU.backend == "cpu"

if IS_CPU_ONLY:
    if TOTAL_RAM_MB < 16384:  # less than 16 GB RAM
        MODEL_FILE = "Qwen_Qwen3-8B-Q3_K_M.gguf"
    else:
        MODEL_FILE = "Qwen_Qwen3-8B-Q4_K_M.gguf"
else:
    MODEL_FILE = "Qwen_Qwen3-8B-Q5_K_M.gguf"

MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILE)

# ──────────────────────── LLM Inference Settings ────────────────────────
# Auto-tuned by platform_setup.py based on detected hardware.
# Override any value here to lock it regardless of platform.
LLM_CONFIG = dict(OPTIMAL_CONFIG)  # copy auto-detected values

# Qwen3-specific overrides (non-thinking mode)
LLM_CONFIG["temperature"] = 0.7
LLM_CONFIG["top_p"] = 0.8
LLM_CONFIG["top_k"] = 20
LLM_CONFIG["repeat_penalty"] = 1.15

# ──────────────────────── Pipeline Tuning (CPU vs GPU) ────────────────────────
# These control how much work the pipeline does at each stage.
# CPU users get a leaner pipeline to keep response times reasonable.

if IS_CPU_ONLY:
    # CPU: faster routing, shorter responses, limited reflection
    ROUTER_MAX_TOKENS = 100          # router output is ~60-80 tokens
    REFLECTION_ENABLED = False       # skip reflection+refinement (~10-20s saved)
    THINKING_ENABLED = True          # enabled — complex queries get lightweight thinking
    CONTEXT_BUDGET_RESERVE = 200     # tokens reserved for overhead

    if TOTAL_RAM_MB < 16384:
        # Low-RAM CPU: ultra-lean pipeline with Q3_K_M
        RESPONSE_MAX_TOKENS = 1024       # shorter responses for speed
        DEEP_RESEARCH_MAX_CHARS = 2500   # minimal web context
        THINKING_BUDGET_HINT = 40        # very short think block
    else:
        # Standard CPU: moderate pipeline with Q4_K_M
        RESPONSE_MAX_TOKENS = 1536       # shorter responses for speed
        DEEP_RESEARCH_MAX_CHARS = 3500   # less web context to process
        THINKING_BUDGET_HINT = 80        # word budget hint for think block
else:
    # GPU: full pipeline, longer responses, reflection for complex queries
    ROUTER_MAX_TOKENS = 150
    RESPONSE_MAX_TOKENS = LLM_CONFIG["max_tokens"]  # 2048 or 4096
    REFLECTION_ENABLED = True
    DEEP_RESEARCH_MAX_CHARS = 7000
    THINKING_ENABLED = True          # thinking for moderate + complex queries
    THINKING_BUDGET_HINT = 200       # word budget hint for think block (GPU: generous)
    CONTEXT_BUDGET_RESERVE = 100

# ──────────────────────── Router Configuration ────────────────────────
# Controls how user queries are classified to the right agent(s).
#   "hybrid"         — Keywords narrow candidates, LLM makes final decision (fast + accurate)
#   "llm_only"       — Always use full LLM classification (most accurate, slowest)
#   "keyword_first"  — Try fast keyword matching first, fall back to LLM (fastest, least nuance)
ROUTER_MODE = "hybrid"

# ──────────────────────── Market Pre-fetch ────────────────────────
# Pre-fetches standard market data (headlines, rates, prices) in a background
# thread at server startup and refreshes every hour. Eliminates redundant
# "latest news" web searches during query processing.
#   True  — background pre-fetch enabled (recommended)
#   False — disabled, all web data fetched per-query
MARKET_PREFETCH = True

# Default market: India
DEFAULT_CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"
DEFAULT_EXCHANGE = "NSE"  # National Stock Exchange of India

# Indian number system formatting thresholds
# 1 Lakh = 1,00,000 | 1 Crore = 1,00,00,000
INDIAN_NUMBER_SYSTEM = True

# ──────────────────────── Portfolio / DMAT Integration ────────────────────────
PORTFOLIO_DB = os.path.join(BASE_DIR, "data", "portfolio.db")

# Broker API credentials — set via environment variables for security.
# Format: FINANCEGPT_<BROKER>_API_KEY, FINANCEGPT_<BROKER>_API_SECRET
BROKER_CONFIGS: dict[str, dict] = {
    "zerodha": {
        "api_key": os.environ.get("FINANCEGPT_ZERODHA_API_KEY", ""),
        "api_secret": os.environ.get("FINANCEGPT_ZERODHA_API_SECRET", ""),
    },
    "upstox": {
        "api_key": os.environ.get("FINANCEGPT_UPSTOX_API_KEY", ""),
        "api_secret": os.environ.get("FINANCEGPT_UPSTOX_API_SECRET", ""),
    },
    "angelone": {
        "api_key": os.environ.get("FINANCEGPT_ANGELONE_API_KEY", ""),
        "api_secret": os.environ.get("FINANCEGPT_ANGELONE_API_SECRET", ""),
    },
    "dhan": {
        "api_key": os.environ.get("FINANCEGPT_DHAN_API_KEY", ""),
        "api_secret": os.environ.get("FINANCEGPT_DHAN_API_SECRET", ""),
    },
    "fivepaisa": {
        "api_key": os.environ.get("FINANCEGPT_FIVEPAISA_API_KEY", ""),
        "api_secret": os.environ.get("FINANCEGPT_FIVEPAISA_API_SECRET", ""),
        "encryption_key": os.environ.get("FINANCEGPT_FIVEPAISA_ENCRYPTION_KEY", ""),
    },
    "icici_direct": {
        "api_key": os.environ.get("FINANCEGPT_ICICI_API_KEY", ""),
        "api_secret": os.environ.get("FINANCEGPT_ICICI_API_SECRET", ""),
    },
    "kotak": {
        "api_key": os.environ.get("FINANCEGPT_KOTAK_API_KEY", ""),
        "api_secret": os.environ.get("FINANCEGPT_KOTAK_API_SECRET", ""),
    },
}

# ──────────────────────── Proxy & Network (Air-tight Environments) ────────────────────────
# Enable PROXY_ENABLED and set PROXY_URL to route HTTP/HTTPS traffic through a proxy.
# Useful for corporate/air-gapped networks. Disable when direct internet access is available.
PROXY_ENABLED = False
PROXY_URL = ""  # e.g. "http://proxy.corp.example.com:8080"

# Custom pip index URL for air-tight environments (used by model_converter and start.py)
# Leave empty to use default PyPI.
PIP_INDEX_URL = ""  # e.g. "https://nexus.corp.example.com/repository/pypi/simple"
PIP_TRUSTED_HOST = ""  # e.g. "nexus.corp.example.com"

# ──────────────────────── Timeout Configuration ────────────────────────
# Per-token wait timeout (seconds). On CPU-only, model generation can be slow.
# Increase this if you see timeout errors during generation.
if IS_CPU_ONLY:
    PER_TOKEN_TIMEOUT = 300  # 5 minutes for CPU (some tokens take 2-3 min)
else:
    PER_TOKEN_TIMEOUT = 120  # 2 minutes for GPU


def get_proxies() -> dict:
    """Return proxy dict for requests/yfinance, or empty dict if disabled."""
    if PROXY_ENABLED and PROXY_URL:
        return {"http": PROXY_URL, "https": PROXY_URL}
    return {}

# ──────────────────────── Cloud LLM Configuration ────────────────────────
# Set USE_CLOUD_LLM = True to skip local model loading and use a cloud-hosted
# LLM via the OpenAI-compatible chat completions API.
#
# Works with: OpenAI, Azure OpenAI, Anthropic (via proxy), Google Gemini,
#             Groq, Together AI, Fireworks, Ollama, LM Studio, vLLM, etc.
#
# Set CLOUD_API_KEY via environment variable for security:
#   export FINANCEGPT_CLOUD_API_KEY="sk-..."
#
USE_CLOUD_LLM = False

CLOUD_LLM = {
    "api_base": "",       # e.g. "https://api.openai.com/v1"
                          #      "https://api.groq.com/openai/v1"
                          #      "https://api.together.xyz/v1"
                          #      "https://generativelanguage.googleapis.com/v1beta/openai"
                          #      "http://localhost:11434/v1"  (Ollama)
    "api_key": os.environ.get("FINANCEGPT_CLOUD_API_KEY", ""),
    "model": "",          # e.g. "gpt-4o-mini", "llama-3.1-70b-versatile",
                          #      "gemini-2.0-flash", "deepseek-r1"
    "temperature": 0.7,
    "max_tokens": 2048,
    "timeout": 60,        # seconds per API call
}


# Agent names
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

AGENT_ICONS = {
    "stock_analyst": "📈",
    "portfolio_manager": "💼",
    "tax_advisor": "🏛️",
    "retirement_planner": "🏖️",
    "loan_advisor": "🏠",
    "budget_planner": "💰",
    "crypto_analyst": "₿",
    "insurance_advisor": "🛡️",
    "mutual_fund_advisor": "📊",
    "general_advisor": "🧠",
}
