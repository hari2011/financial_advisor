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
# Qwen3 8B Q5_K_M (April 2025)
# Hybrid thinking/non-thinking model, superior reasoning vs Qwen 2.5
# Standard transformer architecture — fully compatible with llama-cpp-python
MODEL_REPO = "bartowski/Qwen_Qwen3-8B-GGUF"
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

# ──────────────────────── Router Configuration ────────────────────────
# Controls how user queries are classified to the right agent(s).
#   "keyword_first"  — Try fast keyword matching first, fall back to LLM (fastest)
#   "llm_only"       — Always use LLM classification (most accurate, ~5s slower)
ROUTER_MODE = "llm_only"

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
