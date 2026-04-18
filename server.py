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

    if not query:
        return JSONResponse({"error": "Empty query"}, status_code=400)

    # Resolve / create session
    if not session_id:
        session_id = uuid.uuid4().hex[:16]

    graph = request.app.state.graph
    session_files = _session_files.get(session_id, [])

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
    logger.info(f"Session cleared: {session_id}")
    return {"status": "ok"}


# ──────────────────────── Main ────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8501, reload=False, log_level="info")
