"""
FinanceGPT — FastAPI Backend
Server-Sent Events with token streaming.
LangGraph handles orchestration, history, and checkpointing.
"""
import sys
import os
import time
import json
import logging
import asyncio
import uuid
from contextlib import asynccontextmanager

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Signal platform_setup to print system info on first import
os.environ["FINANCEGPT_STARTUP"] = "1"

# ──────────────────────── Logging (stdout only) ────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("financegpt")

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from agents.router import route_query, list_agents, AGENT_REGISTRY
from config import AGENTS, AGENT_ICONS
from tools.file_parser import parse_file
from tools.calculator_registry import list_calculators, run_calculator

# ──────────────────────── Upload storage ────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory map: session_id -> [{filename, type, content, error}]
_session_files: dict[str, list[dict]] = {}

# ──────────────────────── Session metadata DB ────────────────────────
import aiosqlite

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions", "session_meta.db")

async def _init_session_db():
    """Create session metadata table if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New conversation',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                saved INTEGER NOT NULL DEFAULT 1,
                pinned INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Add pinned column to existing DBs (safe to run multiple times)
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass  # Column already exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)
        await db.commit()


async def _upsert_session(session_id: str, title: str = None, msg_count_delta: int = 0):
    """Create or update session metadata."""
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchall(
            "SELECT title, message_count FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        if row:
            existing_title, existing_count = row[0]
            new_title = title if title else existing_title
            new_count = existing_count + msg_count_delta
            await db.execute(
                "UPDATE sessions SET title = ?, updated_at = ?, message_count = ? WHERE session_id = ?",
                (new_title, now, new_count, session_id)
            )
        else:
            await db.execute(
                "INSERT INTO sessions (session_id, title, created_at, updated_at, message_count) VALUES (?, ?, ?, ?, ?)",
                (session_id, title or "New conversation", now, now, max(msg_count_delta, 0))
            )
        await db.commit()


MAX_UNPINNED_SESSIONS = 5  # Keep only this many unpinned sessions


async def _purge_old_sessions(keep: int = MAX_UNPINNED_SESSIONS):
    """Delete oldest unpinned sessions beyond the keep limit.
    Pinned sessions are never purged."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Get unpinned sessions ordered by most recent, skip the first `keep`
        rows = await db.execute_fetchall(
            "SELECT session_id FROM sessions WHERE pinned = 0 ORDER BY updated_at DESC LIMIT -1 OFFSET ?",
            (keep,)
        )
        if rows:
            ids_to_delete = [r[0] for r in rows]
            placeholders = ",".join("?" * len(ids_to_delete))
            await db.execute(f"DELETE FROM session_files WHERE session_id IN ({placeholders})", ids_to_delete)
            await db.execute(f"DELETE FROM sessions WHERE session_id IN ({placeholders})", ids_to_delete)
            await db.commit()
            logger.info(f"Purged {len(ids_to_delete)} old sessions")


async def _save_session_files(session_id: str, files: list[dict]):
    """Persist uploaded files to DB for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        for f in files:
            # Check if already stored (avoid duplicates)
            existing = await db.execute_fetchall(
                "SELECT id FROM session_files WHERE session_id = ? AND filename = ?",
                (session_id, f.get("filename", ""))
            )
            if not existing:
                await db.execute(
                    "INSERT INTO session_files (session_id, filename, file_type, content) VALUES (?, ?, ?, ?)",
                    (session_id, f.get("filename", ""), f.get("type", ""), f.get("content", ""))
                )
        await db.commit()


async def _load_session_files(session_id: str) -> list[dict]:
    """Load persisted files for a session from DB."""
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await db.execute_fetchall(
            "SELECT filename, file_type, content FROM session_files WHERE session_id = ?",
            (session_id,)
        )
        return [{"filename": r[0], "type": r[1], "content": r[2]} for r in rows]


# ──────────────────────── LangGraph Workflow ────────────────────────
from graph.workflow import build_graph, stream_workflow
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


# ──────────────────────── Lifespan ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FinanceGPT starting up...")
    # Pre-load the LLM on startup so first query is fast
    from llm.engine import llm
    llm.initialize()

    # Start background market data pre-fetcher (refreshes every hour)
    from config import MARKET_PREFETCH
    if MARKET_PREFETCH:
        from tools.market_prefetch import start_prefetch
        start_prefetch()

    # Initialize LangGraph checkpointer + graph
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions", "checkpoints.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Initialize session metadata DB
    await _init_session_db()

    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        app.state.graph = graph
        app.state.checkpointer = checkpointer
        logger.info("LangGraph workflow compiled with SQLite checkpointer.")
        logger.info("FinanceGPT ready.")
        yield

    logger.info("FinanceGPT shutting down.")


app = FastAPI(title="FinanceGPT", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache headers for static assets (skip HTML so users always get fresh pages)
@app.middleware("http")
async def static_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") and not path.endswith(".html"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    return response

# Serve static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ──────────────────────── Routes ────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(STATIC_DIR, "index.html")
    with open(html_path, "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/agents")
async def get_agents():
    """List all available agents."""
    agents = []
    for key, agent in AGENT_REGISTRY.items():
        agents.append({
            "key": key,
            "name": agent.name,
            "icon": AGENT_ICONS.get(key, "🤖"),
            "description": agent.description,
        })
    return agents


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), session_id: str = ""):
    """Upload a file and parse its contents for use in chat context."""
    ALLOWED_EXT = {".csv", ".txt", ".md", ".log", ".json", ".pdf", ".xlsx", ".xls"}
    MAX_SIZE = 50 * 1024 * 1024  # 50MB

    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXT:
        return JSONResponse(
            {"error": f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXT))}"},
            status_code=400,
        )

    # Read with size check
    content_bytes = await file.read()
    if len(content_bytes) > MAX_SIZE:
        return JSONResponse({"error": "File too large. Max 50MB."}, status_code=400)

    # Save to temp file for parsing
    safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    try:
        with open(filepath, "wb") as f:
            f.write(content_bytes)

        # Parse
        result = parse_file(filepath, filename)
        logger.info(f"Upload: {filename} ({ext}) → {len(result.get('content', ''))} chars, error={result.get('error')}")

        # Store parsed content for session
        if not session_id:
            session_id = uuid.uuid4().hex[:16]
        if session_id not in _session_files:
            _session_files[session_id] = []
        _session_files[session_id].append(result)

        return {
            "filename": filename,
            "type": result["type"],
            "chars": len(result.get("content", "")),
            "error": result.get("error"),
            "session_id": session_id,
        }
    finally:
        # Clean up temp file
        try:
            os.remove(filepath)
        except OSError:
            pass


@app.delete("/api/upload/{session_id}")
async def clear_uploads(session_id: str):
    """Clear uploaded files for a session."""
    _session_files.pop(session_id, None)
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(request: Request):
    """Process a chat message with token-level SSE streaming via LangGraph workflow."""
    body = await request.json()
    query = body.get("query", "").strip()
    agent_key = body.get("agent", "auto")
    session_id = body.get("session_id", None)
    save_conversation = body.get("save_conversation", True)

    if not query:
        return JSONResponse({"error": "Empty query"}, status_code=400)

    # Resolve / create session
    if not session_id:
        session_id = uuid.uuid4().hex[:16]

    graph = request.app.state.graph

    # Load files from in-memory first, then DB fallback (for restored sessions)
    session_files = _session_files.get(session_id, [])
    if not session_files:
        session_files = await _load_session_files(session_id)
        if session_files:
            _session_files[session_id] = session_files

    async def event_stream():
        def send_event(event: str, data: dict):
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        # Send session id to client so it can persist it
        yield send_event("session", {"session_id": session_id})

        logger.info(f"Query: {query[:120]} | session={session_id}")

        try:
            async for evt in stream_workflow(
                graph=graph,
                query=query,
                session_id=session_id,
                manual_agent=agent_key,
                session_files=session_files,
            ):
                yield send_event(evt["event"], evt["data"])
        except Exception as e:
            logger.error(f"Workflow error: {e}")
            yield send_event("error", {"message": str(e)})

        # After streaming completes, save session metadata
        if save_conversation:
            # Auto-title from first message (first 60 chars, clean)
            title = query[:60].strip()
            if len(query) > 60:
                title = title.rsplit(' ', 1)[0] + '...'
            await _upsert_session(session_id, title=title, msg_count_delta=1)
            # Persist uploaded files to DB
            if session_files:
                await _save_session_files(session_id, session_files)
            # Auto-purge old unpinned sessions beyond limit
            await _purge_old_sessions()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ──────────────────────── Calculator API ────────────────────────

@app.get("/api/calculators")
async def get_calculators():
    """List all available standalone financial calculators with field definitions."""
    return list_calculators()


@app.post("/api/calculate")
async def calculate(request: Request):
    """Run a financial calculator with given inputs."""
    body = await request.json()
    calc_id = body.get("calculator", "").strip()
    inputs = body.get("inputs", {})

    if not calc_id:
        return JSONResponse({"error": "Missing 'calculator' field"}, status_code=400)

    result = run_calculator(calc_id, inputs)
    if "error" in result:
        logger.warning(f"Calculator error [{calc_id}]: {result['error']} | inputs={inputs}")
        return JSONResponse(result, status_code=400)

    return result


# ──────────────────────── Live Market Data API ────────────────────────

@app.get("/api/market/snapshot")
async def market_snapshot():
    """Get comprehensive market snapshot — indices, gold, forex, commodities, rates.
    Uses pre-cached data if available (instant), falls back to live fetch."""
    from tools.market_prefetch import get_market_snapshot_cached
    from tools.live_market import get_market_snapshot

    # Try pre-cached first (instant)
    snapshot = get_market_snapshot_cached()
    if not snapshot:
        # Fallback: live fetch (may take 2-5s on first call)
        snapshot = await asyncio.to_thread(get_market_snapshot)
    return snapshot


@app.get("/api/market/indices")
async def market_indices():
    """Get live Indian market indices (Nifty 50, Sensex, Bank Nifty, etc)."""
    from tools.live_market import get_indices
    return await asyncio.to_thread(get_indices)


@app.get("/api/market/gold")
async def market_gold():
    """Get live gold price in INR per gram and per 10g."""
    from tools.live_market import get_gold_price_inr
    result = await asyncio.to_thread(get_gold_price_inr)
    if not result:
        return JSONResponse({"error": "Gold price unavailable"}, status_code=503)
    return result


@app.get("/api/market/forex")
async def market_forex():
    """Get live forex rates (USD/INR, EUR/INR, GBP/INR)."""
    from tools.live_market import get_forex
    return await asyncio.to_thread(get_forex)


@app.get("/api/market/stock/{symbol}")
async def market_stock(symbol: str):
    """Get live stock quote for an NSE/BSE stock.
    Example: /api/market/stock/RELIANCE"""
    from tools.live_market import get_stock_quote
    result = await asyncio.to_thread(get_stock_quote, symbol)
    if not result:
        return JSONResponse(
            {"error": f"Stock '{symbol}' not found. Use NSE symbol (e.g., RELIANCE, TCS, INFY)"},
            status_code=404,
        )
    return result


@app.get("/api/market/mf/{scheme_code}")
async def market_mutual_fund(scheme_code: str):
    """Get latest NAV for a mutual fund by AMFI scheme code.
    Example: /api/market/mf/119551"""
    from tools.live_market import get_mutual_fund_nav
    result = await asyncio.to_thread(get_mutual_fund_nav, scheme_code)
    if not result:
        return JSONResponse(
            {"error": f"Mutual fund scheme '{scheme_code}' not found"},
            status_code=404,
        )
    return result


@app.get("/api/market/mf/search/{query}")
async def market_mf_search(query: str):
    """Search mutual funds by name. Returns list of matching schemes.
    Example: /api/market/mf/search/hdfc+flexi+cap"""
    from tools.live_market import search_mutual_fund
    results = await asyncio.to_thread(search_mutual_fund, query)
    return results


@app.get("/api/market/rates")
async def market_rates():
    """Get current FD, PPF, EPF, and savings scheme interest rates."""
    from tools.live_market import get_fd_rates
    return get_fd_rates()


@app.get("/api/health")
async def health():
    from llm.engine import llm, _response_cache
    from tools.calculator_registry import _calc_cache
    return {
        "status": "ok",
        "llm_loaded": llm._initialized,
        "agents": len(AGENT_REGISTRY),
        "cache": {
            "response_cache_size": _response_cache.size,
            "response_cache_hits": _response_cache.hits,
            "response_cache_misses": _response_cache.misses,
            "calculator_cache_size": len(_calc_cache),
        },
    }


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history and uploaded files for a session."""
    _session_files.pop(session_id, None)
    # Remove from metadata DB
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM session_files WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await db.commit()
    logger.info(f"Session cleared: {session_id}")
    return {"status": "ok"}


# ──────────────────────── Session History API ────────────────────────

@app.get("/api/sessions")
async def list_sessions():
    """List all saved conversation sessions, most recent first."""
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await db.execute_fetchall(
            "SELECT session_id, title, created_at, updated_at, message_count, pinned "
            "FROM sessions WHERE saved = 1 ORDER BY pinned DESC, updated_at DESC LIMIT 50"
        )
    return [
        {
            "session_id": r[0],
            "title": r[1],
            "created_at": r[2],
            "updated_at": r[3],
            "message_count": r[4],
            "pinned": bool(r[5]),
        }
        for r in rows
    ]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, request: Request):
    """Restore a conversation session — returns past exchanges from checkpoint."""
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}

    try:
        snapshot = await graph.aget_state(config)
        if not snapshot or not snapshot.values:
            return JSONResponse({"error": "Session not found"}, status_code=404)

        state = snapshot.values
        past_exchanges = state.get("past_exchanges", [])
        profile = state.get("profile", {})

        return {
            "session_id": session_id,
            "exchanges": past_exchanges,
            "profile": profile,
        }
    except Exception as e:
        logger.error(f"Failed to restore session {session_id}: {e}")
        return JSONResponse({"error": "Failed to restore session"}, status_code=500)


@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, request: Request):
    """Update a conversation session (rename or pin/unpin)."""
    body = await request.json()
    async with aiosqlite.connect(DB_PATH) as db:
        if "title" in body:
            new_title = body["title"].strip()[:100]
            if not new_title:
                return JSONResponse({"error": "Title cannot be empty"}, status_code=400)
            await db.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ?",
                (new_title, time.time(), session_id)
            )
        if "pinned" in body:
            pinned = 1 if body["pinned"] else 0
            await db.execute(
                "UPDATE sessions SET pinned = ? WHERE session_id = ?",
                (pinned, session_id)
            )
            logger.info(f"Session {session_id} {'pinned' if pinned else 'unpinned'}")
        await db.commit()
    return {"status": "ok"}


# ──────────────────────── Main ────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8501, reload=False, log_level="info")
