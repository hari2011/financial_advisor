# API Reference

Complete REST API documentation for FinanceGPT.

**Base URL**: `http://localhost:8501`

---

## Table of Contents

- [Chat (SSE Streaming)](#chat-sse-streaming)
- [Calculators](#calculators)
- [Market Data](#market-data)
- [File Upload](#file-upload)
- [Sessions](#sessions)
- [Agents](#agents)
- [System Health](#system-health)

---

## Chat (SSE Streaming)

### `POST /api/chat`

Send a financial question and receive a streaming response via Server-Sent Events (SSE).

**Request:**

```bash
curl -X POST http://localhost:8501/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SIP of ₹10K per month for 20 years at 12%",
    "agent": "auto",
    "session_id": "optional-session-id"
  }'
```

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | string | ✅ | — | The user's financial question |
| `agent` | string | ❌ | `"auto"` | Force a specific agent or `"auto"` for LLM routing |
| `session_id` | string | ❌ | auto-generated | Session ID for conversation continuity |

**Response**: SSE stream with the following event types:

| Event Type | Payload | Description |
|------------|---------|-------------|
| `session` | `{ session_id: "abc123" }` | Session identifier for this conversation |
| `status` | `{ message: "Analyzing query..." }` | Pipeline progress updates |
| `agent` | `{ agents: ["mutual_fund_advisor"], complexity: "moderate" }` | Selected agents and query complexity |
| `thinking` | `{ content: "Let me analyze..." }` | LLM internal reasoning (GPU + complex only) |
| `token` | `{ content: "A" }` | One token of the response (streamed) |
| `done` | `{ timing: { route: 1.2, context: 2.1, ... }, tokens: 312 }` | Completion signal with timing breakdown |
| `error` | `{ message: "Error details" }` | Error message if something fails |

**SSE Example (raw):**

```
data: {"type": "session", "session_id": "a1b2c3d4"}

data: {"type": "status", "message": "Analyzing your query..."}

data: {"type": "agent", "agents": ["mutual_fund_advisor"], "complexity": "moderate"}

data: {"type": "status", "message": "Running SIP calculator..."}

data: {"type": "token", "content": "A"}

data: {"type": "token", "content": " SIP"}

data: {"type": "token", "content": " of"}

data: {"type": "done", "timing": {"route": 1.2, "context": 2.3, "generate": 8.5, "total": 12.1}, "tokens": 312}
```

**JavaScript client example:**

```javascript
const eventSource = new EventSource('/api/chat?' + new URLSearchParams({
  query: 'SIP of ₹10K for 20 years at 12%'
}));

// Note: In practice, use POST via fetch + ReadableStream
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'SIP of ₹10K for 20 years at 12%' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const text = decoder.decode(value);
  const lines = text.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      
      switch (event.type) {
        case 'token':
          // Append to response display
          appendToken(event.content);
          break;
        case 'thinking':
          // Show in thinking block
          appendThinking(event.content);
          break;
        case 'done':
          // Show timing
          showTiming(event.timing);
          break;
      }
    }
  }
}
```

---

## Calculators

### `GET /api/calculators`

List all 36 available calculators with their field definitions.

**Request:**

```bash
curl http://localhost:8501/api/calculators
```

**Response:**

```json
{
  "calculators": [
    {
      "id": "sip",
      "name": "SIP Calculator",
      "icon": "📈",
      "fields": [
        {
          "name": "monthly_investment",
          "label": "Monthly Investment (₹)",
          "type": "number",
          "min": 100,
          "max": 10000000,
          "default": 10000,
          "required": true
        },
        {
          "name": "annual_rate",
          "label": "Expected Annual Return (%)",
          "type": "number",
          "min": 1,
          "max": 50,
          "default": 12,
          "required": true
        },
        {
          "name": "years",
          "label": "Investment Period (Years)",
          "type": "number",
          "min": 1,
          "max": 50,
          "default": 20,
          "required": true
        }
      ]
    },
    // ... 35 more calculators
  ]
}
```

### `POST /api/calculate`

Run a specific calculator with input values.

**Request:**

```bash
curl -X POST http://localhost:8501/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "calculator": "sip",
    "inputs": {
      "monthly_investment": "10000",
      "annual_rate": "12",
      "years": "20"
    }
  }'
```

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `calculator` | string | ✅ | Calculator ID (e.g., `sip`, `emi`, `income_tax`) |
| `inputs` | object | ✅ | Key-value pairs matching the calculator's field definitions |

**Response:**

```json
{
  "success": true,
  "calculator": "sip",
  "result": {
    "future_value": 9991479,
    "total_invested": 2400000,
    "wealth_gained": 7591479,
    "wealth_multiplier": "4.16x",
    "formatted_output": "...",
    "milestones": [
      { "year": 5, "value": 823483 },
      { "year": 10, "value": 2323283 }
    ],
    "delay_cost": {
      "1_year": 1123456,
      "3_years": 3456789,
      "5_years": 5678901
    }
  }
}
```

**Calculator IDs:**

| ID | Calculator |
|----|-----------|
| `sip` | SIP Calculator |
| `lumpsum` | Lumpsum Calculator |
| `step_up_sip` | Step-Up SIP |
| `goal_sip` | Goal-Based SIP |
| `sip_vs_lumpsum` | SIP vs Lumpsum Comparison |
| `mf_returns` | Mutual Fund Returns |
| `compound_interest` | Compound Interest |
| `simple_interest` | Simple Interest |
| `xirr` | XIRR Calculator |
| `ppf` | PPF Calculator |
| `ssy` | Sukanya Samriddhi Yojana |
| `epf` | EPF Calculator |
| `nps` | NPS Calculator |
| `nsc` | NSC Calculator |
| `scss` | SCSS Calculator |
| `pomis` | Post Office MIS |
| `apy` | Atal Pension Yojana |
| `kvp` | Kisan Vikas Patra |
| `fd` | FD Calculator |
| `rd` | RD Calculator |
| `emi` | EMI Calculator |
| `education_loan` | Education Loan |
| `loan_prepayment` | Loan Prepayment |
| `flat_vs_reducing` | Flat vs Reducing Rate |
| `income_tax` | Income Tax (New vs Old) |
| `ctc` | CTC to Take-Home |
| `capital_gains` | Capital Gains Tax |
| `hra` | HRA Exemption |
| `gst` | GST Calculator |
| `tds` | TDS Calculator |
| `gratuity` | Gratuity Calculator |
| `retirement` | Retirement Planner |
| `fire` | FIRE Calculator |
| `inflation_goal` | Inflation Goal Planner |
| `salary_hike` | Salary Hike Analyzer |
| `swp` | SWP Calculator |

---

## Market Data

### `GET /api/market/snapshot`

Full market overview — indices, gold, forex, interest rates.

```bash
curl http://localhost:8501/api/market/snapshot
```

```json
{
  "indices": {
    "nifty_50": { "price": 24356.50, "change": 0.85, "timestamp": "..." },
    "sensex": { "price": 80147.23, "change": 0.72, "timestamp": "..." },
    "bank_nifty": { "price": 52000.00, "change": 1.12, "timestamp": "..." }
  },
  "gold": {
    "price_per_gram_24k": 7845.00,
    "price_per_10g_24k": 78450.00,
    "price_per_gram_22k": 7191.25,
    "price_per_10g_22k": 71912.50,
    "price_per_gram_18k": 5883.75,
    "price_per_10g_18k": 58837.50
  },
  "forex": {
    "usd_inr": 83.45,
    "eur_inr": 91.23,
    "gbp_inr": 106.78
  },
  "rates": {
    "repo_rate": 6.50,
    "fd_rate": "6.5-7.5%",
    "ppf_rate": 7.10,
    "epf_rate": 8.25
  }
}
```

### `GET /api/market/indices`

Live index values.

```bash
curl http://localhost:8501/api/market/indices
```

### `GET /api/market/gold`

Gold prices in INR for all purities.

```bash
curl http://localhost:8501/api/market/gold
```

```json
{
  "price_per_gram_24k": 7845.00,
  "price_per_10g_24k": 78450.00,
  "price_per_gram_22k": 7191.25,
  "price_per_10g_22k": 71912.50,
  "price_per_gram_18k": 5883.75,
  "price_per_10g_18k": 58837.50,
  "source": "COMEX × USD/INR",
  "timestamp": "2026-05-02T10:30:00Z"
}
```

### `GET /api/market/forex`

Foreign exchange rates against INR.

```bash
curl http://localhost:8501/api/market/forex
```

### `GET /api/market/stock/{symbol}`

Live quote for any NSE/BSE stock.

```bash
# NSE stock (append .NS)
curl http://localhost:8501/api/market/stock/RELIANCE.NS

# BSE stock (append .BO)
curl http://localhost:8501/api/market/stock/RELIANCE.BO
```

```json
{
  "symbol": "RELIANCE.NS",
  "name": "Reliance Industries Limited",
  "price": 2456.80,
  "change": -12.30,
  "change_percent": -0.50,
  "open": 2470.00,
  "high": 2475.50,
  "low": 2445.00,
  "volume": 12345678,
  "market_cap": 1672000000000,
  "pe_ratio": 28.5,
  "52w_high": 3025.00,
  "52w_low": 2220.00
}
```

### `GET /api/market/mf/{scheme_code}`

Mutual fund NAV by AMFI scheme code.

```bash
curl http://localhost:8501/api/market/mf/119551
```

### `GET /api/market/mf/search/{query}`

Search mutual funds by name.

```bash
curl http://localhost:8501/api/market/mf/search/parag%20parikh%20flexi
```

### `GET /api/market/rates`

Current Indian interest rates.

```bash
curl http://localhost:8501/api/market/rates
```

---

## File Upload

### `POST /api/upload`

Upload a financial document for AI analysis.

```bash
curl -X POST http://localhost:8501/api/upload \
  -F "file=@portfolio.csv" \
  -F "session_id=abc123"
```

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `file` | file | ✅ | The file to upload |
| `session_id` | string | ✅ | Session to attach the file to |

**Supported formats**: CSV, PDF, Excel (.xlsx, .xls), JSON, TXT

**Response:**

```json
{
  "success": true,
  "filename": "portfolio.csv",
  "type": "csv",
  "rows": 45,
  "columns": ["Date", "Fund", "Amount", "NAV", "Units"],
  "preview": "First 5 rows..."
}
```

### `DELETE /api/upload/{session_id}`

Clear all uploaded files for a session.

```bash
curl -X DELETE http://localhost:8501/api/upload/abc123
```

---

## Sessions

### `DELETE /api/session/{session_id}`

Clear conversation history for a session.

```bash
curl -X DELETE http://localhost:8501/api/session/abc123
```

---

## Agents

### `GET /api/agents`

List all available specialist agents.

```bash
curl http://localhost:8501/api/agents
```

```json
{
  "agents": [
    {
      "id": "stock_analyst",
      "name": "Stock Market Analyst (NSE/BSE)",
      "icon": "📈"
    },
    {
      "id": "mutual_fund_advisor",
      "name": "Mutual Fund Advisor",
      "icon": "📊"
    },
    {
      "id": "portfolio_manager",
      "name": "Portfolio Manager",
      "icon": "💼"
    },
    {
      "id": "tax_advisor",
      "name": "Tax & Compliance Advisor (India)",
      "icon": "🏛️"
    },
    {
      "id": "retirement_planner",
      "name": "Retirement & SIP Planner",
      "icon": "🏖️"
    },
    {
      "id": "loan_advisor",
      "name": "Loan & EMI Advisor",
      "icon": "🏠"
    },
    {
      "id": "budget_planner",
      "name": "Budget & Savings Planner",
      "icon": "💰"
    },
    {
      "id": "crypto_analyst",
      "name": "Cryptocurrency Analyst",
      "icon": "₿"
    },
    {
      "id": "insurance_advisor",
      "name": "Insurance Advisor (India)",
      "icon": "🛡️"
    },
    {
      "id": "mutual_fund_advisor",
      "name": "Mutual Fund Advisor",
      "icon": "📊"
    },
    {
      "id": "general_advisor",
      "name": "General Financial Advisor",
      "icon": "🧠"
    }
  ]
}
```

---

## System Health

### `GET /api/health`

System info, LLM status, and cache statistics.

```bash
curl http://localhost:8501/api/health
```

```json
{
  "status": "ok",
  "llm_loaded": true,
  "model": "Qwen_Qwen3-8B-Q5_K_M.gguf",
  "gpu_backend": "metal",
  "agents": 10,
  "calculators": 36,
  "cache": {
    "response_cache_size": 12,
    "response_cache_hits": 45,
    "response_cache_misses": 67,
    "calculator_cache_size": 8,
    "router_cache_size": 5
  },
  "system": {
    "os": "Darwin",
    "arch": "arm64",
    "ram_mb": 18432,
    "cpu_threads": 8,
    "gpu": "Apple M3 Pro",
    "context_window": 24576,
    "pipeline": "GPU-accelerated (full)"
  }
}
```

---

## Error Handling

All endpoints return standard error responses:

```json
{
  "error": true,
  "message": "Calculator 'xyz' not found",
  "status_code": 404
}
```

| Status Code | Meaning |
|:-----------:|---------|
| 200 | Success |
| 400 | Bad request (invalid inputs, missing required fields) |
| 404 | Resource not found (invalid calculator ID, stock symbol) |
| 500 | Internal server error (LLM failure, unexpected error) |

---

## Rate Limits

There are no API rate limits — the server runs locally on your machine. However:
- Only one LLM inference runs at a time (requests are queued)
- Market data calls to yfinance are rate-limited internally (0.5s between requests)
- Web search calls to DuckDuckGo are rate-limited internally (0.5-1.75s between requests)
