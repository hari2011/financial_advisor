# User Guide

Everything you need to know to use FinanceGPT effectively.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Chat Interface](#chat-interface)
  - [Asking Questions](#asking-questions)
  - [Understanding Responses](#understanding-responses)
  - [Thinking Blocks](#thinking-blocks)
  - [Follow-Up Suggestions](#follow-up-suggestions)
  - [Conversation Controls](#conversation-controls)
- [Financial Calculators](#financial-calculators)
  - [Using the Calculator Grid](#using-the-calculator-grid)
  - [Calculator Outputs](#calculator-outputs)
  - [Full Calculator List](#full-calculator-list)
- [Market Ticker](#market-ticker)
- [File Upload & Analysis](#file-upload--analysis)
- [Sessions & History](#sessions--history)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Tips for Better Answers](#tips-for-better-answers)
- [What FinanceGPT Can Do](#what-financegpt-can-do)
- [What FinanceGPT Cannot Do](#what-financegpt-cannot-do)

---

## Getting Started

After launching (`python3 start.py` or `python server.py`), open your browser:

```
http://localhost:8501
```

> **Cloud LLM mode**: If you've set `USE_CLOUD_LLM=True` in config.py, no model download is needed — the app connects to your chosen cloud provider (OpenAI, Groq, Gemini, Ollama, etc.) instantly. See [Cloud LLM Setup](INSTALLATION.md#cloud-llm-setup).

You'll see the FinanceGPT chat interface with:
- **Left sidebar**: Agent list, session manager, file upload, theme toggle
- **Top bar**: Live market ticker (Nifty, Sensex, Gold, USD/INR)
- **Center**: Chat area for asking financial questions
- **Bottom**: Calculator grid (36 financial tools)

---

## Chat Interface

### Asking Questions

Type any financial question in natural language. The AI automatically:
1. **Selects the right expert(s)** — tax advisor for tax questions, loan advisor for EMI queries, etc.
2. **Runs calculations** — if your query involves numbers, they're computed exactly before the AI responds
3. **Fetches live data** — current stock prices, gold rates, forex rates are injected into the answer
4. **Searches the web** — for current news, fund recommendations, and regulatory updates

**Example questions:**

| Category | Question |
|----------|----------|
| **SIP Planning** | "SIP of ₹10,000 per month for 20 years at 12% — what will I get?" |
| **Tax Comparison** | "Salary ₹15 LPA — should I choose old or new tax regime?" |
| **CTC Breakdown** | "CTC ₹24 LPA — what's my monthly take-home?" |
| **Loan Analysis** | "Home loan ₹50 lakh at 8.5% for 20 years — show EMI and total interest" |
| **Prepay vs Invest** | "Should I prepay my home loan or invest the extra in mutual funds?" |
| **Stock Analysis** | "Analyze Reliance Industries — fundamentals and outlook" |
| **Gold Prices** | "What's the current gold price for 24K and 22K?" |
| **FIRE Planning** | "Monthly expenses ₹50K, age 30 — when can I retire?" |
| **Retirement** | "I'm 28, want ₹5 crore by 55 — how much SIP monthly?" |
| **Budget** | "Budget plan for ₹1 lakh monthly salary" |
| **Insurance** | "Best term insurance plans for 30-year-old male, ₹1 Cr cover" |
| **Crypto** | "Should I invest in Bitcoin? What are the taxes in India?" |

### Understanding Responses

Each response contains:

```
┌─ Agent Badge ────────────────────────────────────────────────┐
│  📊 Mutual Fund Advisor                                      │
├──────────────────────────────────────────────────────────────┤
│  Your SIP of ₹10,000/month at 12% for 20 years will grow to:│
│                                                              │
│  💰 Total Corpus: ₹99,91,479                                │
│  📊 Amount Invested: ₹24,00,000                              │
│  📈 Wealth Gained: ₹75,91,479                                │
│  ✨ Wealth Multiplier: 4.16x                                 │
│                                                              │
│  Here's a year-by-year breakdown...                          │
│                                                              │
│  Sources: [1] Groww [2] Moneycontrol                         │
├──────────────────────────────────────────────────────────────┤
│  Follow-up suggestions:                                      │
│  [Step-up SIP comparison] [Lumpsum vs SIP] [Tax on gains]   │
├──────────────────────────────────────────────────────────────┤
│  ⏱ 8.2s · 312 tokens · 22 tok/s                             │
└──────────────────────────────────────────────────────────────┘
```

- **Agent badge**: Which specialist(s) answered your query
- **Pre-computed values**: ₹ amounts are calculated by verified formulas, not hallucinated
- **Citation cards**: `[1]`, `[2]` links to source websites
- **Follow-up chips**: Clickable suggestions for related questions
- **Timing badge**: Click to see per-step performance breakdown

### Thinking Blocks

For complex queries on GPU systems, you'll see a collapsible "Thinking" block:

```
┌─ 🧠 Thinking (3.2s) ─────────────── [▼ collapse] ───┐
│                                                        │
│  Let me analyze this step by step...                   │
│  First, I need to compare the old and new tax regimes  │
│  for a ₹15 LPA salary with the given deductions.      │
│  Under old regime: Basic exemption ₹2.5L, then...     │
│  Under new regime: Basic exemption ₹3L, then...       │
│                                                        │
└────────────────────────────────────────────────────────┘

[Actual response appears below the thinking block]
```

This shows the AI's internal reasoning process in real-time. It's useful for understanding **why** the AI recommends something, not just what it recommends.

> **Note**: Thinking mode is only available on GPU systems for complex queries. CPU systems skip this to keep response times fast.

### Follow-Up Suggestions

After each response, you'll see 3 clickable suggestion chips:

```
[📊 Compare step-up SIP]  [🧮 Show tax on gains]  [📈 Best ELSS funds]
```

Click any chip to ask that follow-up question automatically. The AI remembers your conversation context (your numbers, your scenario).

### Conversation Controls

| Control | Action |
|---------|--------|
| **■ Stop** | Stop the AI mid-response (also: press `Esc`) |
| **🔄 Regenerate** | Re-run the last query for a different answer |
| **👍 / 👎** | Rate the response (stored locally) |
| **📥 Export** | Download the entire conversation as a Markdown file |
| **🗂️ New Chat** | Start a fresh conversation (also: `Cmd+Shift+N`) |

---

## Financial Calculators

### Using the Calculator Grid

The bottom section of the UI has a searchable grid of 36 financial calculators.

1. **Search**: Type in the search box to filter (e.g., "SIP", "tax", "EMI")
2. **Click a calculator**: Opens the input form
3. **Fill in values**: Enter amounts, rates, years
4. **Click Calculate**: See instant results with detailed breakdowns

### Calculator Outputs

Each calculator provides rich output beyond just the final number:

| Feature | Description |
|---------|-------------|
| **Primary result** | The main calculated value (corpus, EMI, tax, etc.) |
| **Wealth multiplier** | How much your money grew (e.g., "4.16x") |
| **Delay cost** | Cost of delaying investment by 1, 3, 5 years |
| **Real returns** | After-inflation returns |
| **Tax impact** | Post-tax values where applicable |
| **Comparisons** | Side-by-side data (e.g., SIP vs Lumpsum, Old vs New regime) |
| **Tips** | Actionable optimization suggestions |

### Full Calculator List

#### Investment & Savings (9 calculators)

| Calculator | What It Calculates |
|-----------|-------------------|
| **SIP** | Future value of monthly investments with year-wise milestones |
| **Lumpsum** | One-time investment growth with doubling time |
| **Step-Up SIP** | SIP with annual increment (e.g., increase ₹500/year) |
| **Goal-Based SIP** | Monthly SIP needed to reach a target corpus |
| **Lumpsum vs SIP** | Side-by-side comparison with verdict |
| **Mutual Fund Returns** | SIP/lumpsum returns with expense ratio impact |
| **Compound Interest** | Monthly/quarterly/annual compounding |
| **Simple Interest** | Basic simple interest calculation |
| **XIRR** | Annualized return for irregular cashflows (SIP, lumpsum mix) |

#### Government Schemes (9 calculators)

| Calculator | What It Calculates |
|-----------|-------------------|
| **PPF** | 15-year maturity with 80C benefit and comparison to taxable FD |
| **SSY** | Sukanya Samriddhi Yojana — 21-year maturity for girl child |
| **EPF** | Employer + employee PF with salary hike projection |
| **NPS** | Corpus at 60, annuity split, 80CCD tax savings |
| **NSC** | 5-year National Savings Certificate with 80C |
| **SCSS** | Senior Citizen savings with quarterly payout |
| **Post Office MIS** | Monthly income scheme with guaranteed returns |
| **APY** | Atal Pension Yojana — pension after 60 |
| **KVP** | Kisan Vikas Patra — months to double your money |

#### Fixed Income (2 calculators)

| Calculator | What It Calculates |
|-----------|-------------------|
| **FD** | Maturity with TDS impact, post-tax return, real return |
| **RD** | Monthly deposit growth with SIP comparison |

#### Loans (4 calculators)

| Calculator | What It Calculates |
|-----------|-------------------|
| **EMI** | Monthly EMI with year-wise amortization table |
| **Education Loan** | EMI with moratorium and 80E tax benefit |
| **Loan Prepayment** | Interest saved and months reduced by prepaying |
| **Flat vs Reducing** | EMI comparison between flat and reducing balance rates |

#### Tax (7 calculators)

| Calculator | What It Calculates |
|-----------|-------------------|
| **Income Tax** | New vs Old regime comparison (FY 2025-26) with slab breakdown |
| **CTC to Take-Home** | Full salary breakdown — Basic, HRA, EPF, deductions |
| **Capital Gains** | STCG/LTCG for equity, debt MF, property, gold, crypto |
| **HRA Exemption** | 3-way minimum rule with optimal rent suggestion |
| **GST** | Inclusive/exclusive with CGST/SGST split |
| **TDS** | 8 income types with PAN/no-PAN rates |
| **Gratuity** | Payment of Gratuity Act formula with tax-free limit |

#### Planning (5 calculators)

| Calculator | What It Calculates |
|-----------|-------------------|
| **Retirement** | Corpus needed, SIP required, emergency buffer |
| **FIRE** | 5 FIRE types — Lean, Regular, Fat, Barista, Coast |
| **Inflation Goal** | Future cost with inflation, SIP needed |
| **Salary Hike** | Take-home impact at different hike percentages |
| **SWP** | Sustainable monthly withdrawal from corpus |

---

## Market Ticker

The scrolling bar at the top shows live market data:

```
📈 Nifty 50: 24,356.50 (+0.85%)  |  📈 Sensex: 80,147.23 (+0.72%)  |
💰 Gold 24K/10g: ₹78,450  |  💰 Gold 22K/10g: ₹71,912  |
💱 USD/INR: ₹83.45
```

- Data refreshes automatically every 5 minutes
- Click on any ticker item to ask a question about it
- Gold prices show both 24K (investment grade) and 22K (standard Indian jewelry)

---

## File Upload & Analysis

Upload financial documents for AI analysis:

1. Click the **📎** icon in the sidebar
2. Upload a file (supported: CSV, PDF, Excel, JSON, TXT)
3. The file content is parsed and injected into the AI's context
4. Ask questions about the uploaded data

**Use cases:**
- Upload a **mutual fund statement** → "Analyze my portfolio allocation"
- Upload a **salary slip PDF** → "Calculate my tax liability"
- Upload a **bank statement CSV** → "Categorize my expenses and suggest a budget"
- Upload an **Excel portfolio** → "What's my XIRR? Should I rebalance?"

**Supported formats:**

| Format | Parser | What's Extracted |
|--------|--------|-----------------|
| CSV | pandas | Full tabular data |
| PDF | PyMuPDF / pdfplumber | Text content, tables |
| Excel (.xlsx, .xls) | openpyxl / xlrd | All sheets, tabular data |
| JSON | Built-in | Structured data |
| TXT | Built-in | Full text content |

---

## Sessions & History

### Managing Sessions

- **New chat**: Click "New Chat" in sidebar or press `Cmd+Shift+N`
- **Switch sessions**: Click any previous session in the sidebar
- **Auto-restore**: Your last active session is automatically restored when you reopen the page
- **Pin important sessions**: Pin icon keeps them from auto-purging
- **Delete session**: Click the delete icon on any session

### Session Memory

The AI remembers context within a session:

```
You:  "I'm 28, earning ₹15 LPA"
AI:   [stores: age=28, income=₹15 LPA]

You:  "How much SIP for retirement?"
AI:   [uses stored age=28, income=₹15 LPA to calculate]
      "Based on your age (28) and income (₹15 LPA), here's your retirement plan..."
```

Facts like age, income, risk appetite, and financial goals persist across turns within the same session.

### Auto-Purge

- The 5 most recent sessions are kept
- Older unpinned sessions are automatically cleaned up
- Pinned sessions are never deleted
- Session data is stored locally in SQLite (never sent anywhere)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line in input |
| `Esc` | Stop generation |
| `/` | Focus input box |
| `Cmd+Shift+N` | New chat session |
| `Cmd+Shift+E` | Export conversation |

---

## Tips for Better Answers

### Be specific with numbers

```
❌ "How much SIP do I need?"
✅ "SIP for ₹5 crore corpus in 25 years at 12% expected return"
```

### Include your context

```
❌ "Should I invest in NPS?"
✅ "I'm 30, in the 30% tax bracket, already maxed 80C — should I invest in NPS for extra deduction?"
```

### Ask comparative questions

```
✅ "Old vs new tax regime for ₹18 LPA with 80C ₹1.5L and HRA ₹12K"
✅ "Should I prepay my ₹40L home loan at 8.5% or invest ₹5L in ELSS?"
✅ "PPF vs ELSS vs NPS — which saves more tax for me?"
```

### Use follow-up chips

After each response, the AI suggests related questions. Click them to explore deeper — the AI remembers your numbers and scenario.

### Multi-agent queries work great

The AI routes complex questions to multiple experts automatically:
- "Compare home loan prepayment vs mutual fund SIP" → Loan Advisor + Mutual Fund Advisor
- "Plan retirement with EPF + NPS + SIP" → Retirement Planner + Tax Advisor
- "₹20 LPA CTC — budget + tax + investment plan" → Budget Planner + Tax Advisor + Portfolio Manager

---

## What FinanceGPT Can Do

| Capability | Details |
|-----------|---------|
| **Indian tax planning** | New/old regime comparison, 80C/80D optimization, CTC breakdown, HRA, capital gains |
| **Investment analysis** | SIP/lumpsum projections, mutual fund selection, stock fundamentals, ELSS vs PPF |
| **Loan planning** | EMI calculation, prepayment analysis, flat vs reducing, PMAY eligibility |
| **Retirement planning** | Corpus estimation, FIRE (5 types), NPS/PPF/EPF optimization |
| **Live market data** | Stock prices, Nifty/Sensex, gold (24K/22K/18K), forex, crypto |
| **Budget advice** | 50/30/20 budgeting, expense categorization, savings rate analysis |
| **Insurance guidance** | Term life sizing, health insurance selection, claim ratios |
| **Crypto awareness** | India-specific 30% flat tax + 1% TDS, exchange comparison |
| **Document analysis** | Parse and analyze uploaded financial documents |
| **Exact calculations** | 36 verified calculators for precise ₹ amounts |

---

## What FinanceGPT Cannot Do

| Limitation | Details |
|-----------|---------|
| **Execute trades** | Cannot buy/sell stocks, MFs, or crypto — advisory only |
| **Access your accounts** | Cannot connect to your bank, demat, or brokerage accounts |
| **Guaranteed predictions** | Market forecasts are opinions based on data, not guarantees |
| **Real-time intraday** | Market data has a few minutes of delay (yfinance limitation) |
| **Legal/regulatory advice** | Not a substitute for a CA, financial planner, or lawyer |
| **NRI taxation** | Primarily focused on resident Indian taxation |
| **US/UK/global markets** | Optimized for Indian markets (NSE/BSE, ₹, INR taxation) |

> **Disclaimer**: FinanceGPT is an educational tool. Always consult a qualified financial advisor (SEBI-registered) before making significant investment decisions.
