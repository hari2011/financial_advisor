"""Background market data pre-fetcher.

Runs standard financial searches at server startup and refreshes every hour.
Pre-cached data is injected into every query's context, eliminating the need
for redundant "latest news" web searches during deep_research.

Categories pre-fetched:
  1. India economy & stock market headlines
  2. Global markets & trade news
  3. RBI/SEBI policy & rate updates
  4. Tax & regulation changes
  5. Gold, forex, commodity prices
"""

import time
import logging
import threading
from datetime import date
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("financegpt.prefetch")

# ── Pre-fetched market briefing cache ──
_prefetch_lock = threading.Lock()
_prefetch_cache: dict = {
    "text": "",
    "ts": 0,
    "categories": {},   # category → list of headline strings
}
_PREFETCH_TTL: int = 3600   # 1 hour
_prefetch_thread: threading.Thread | None = None

# ── Standard queries to pre-fetch (not user-specific) ──
_STANDARD_QUERIES = {
    "india_markets": {
        "query": "India economy stock market Nifty Sensex today",
        "type": "news",
        "max_results": 4,
        "label": "India Markets",
    },
    "global_markets": {
        "query": "global markets US economy tariff trade news today",
        "type": "news",
        "max_results": 3,
        "label": "Global Markets",
    },
    "rbi_policy": {
        "query": "RBI SEBI policy repo rate interest rate India",
        "type": "news",
        "max_results": 3,
        "label": "RBI & Policy",
    },
    "tax_updates": {
        "query": "India income tax GST budget changes 2025 2026",
        "type": "news",
        "max_results": 3,
        "label": "Tax & Regulation",
    },
    "commodities": {
        "query": "gold silver crude oil price India today",
        "type": "news",
        "max_results": 3,
        "label": "Commodities & Forex",
    },
}


def _fetch_category(key: str, spec: dict) -> tuple[str, list[str]]:
    """Fetch one category of standard market news. Returns (key, headlines)."""
    from tools.web_search import _ddgs_with_retry

    try:
        results = _ddgs_with_retry(spec["type"], spec["query"],
                                   max_results=spec["max_results"])
        headlines = []
        for r in results:
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            source = r.get("source", "").strip()
            if title:
                line = f"[{source}] {title}"
                if body:
                    line += f": {body[:120]}"
                headlines.append(line)
        return key, headlines
    except Exception as e:
        logger.warning(f"Pre-fetch {key} failed: {e}")
        return key, []


def _run_prefetch():
    """Execute all standard queries in parallel and build the cached briefing."""
    t0 = time.time()
    logger.info("Market pre-fetch starting...")

    categories = {}
    # Use max 2 workers — DDG's news.js endpoint aggressively rate-limits
    # concurrent requests, even with per-call rate limiting in web_search.
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="prefetch") as pool:
        futures = {
            pool.submit(_fetch_category, key, spec): key
            for key, spec in _STANDARD_QUERIES.items()
        }
        for future in futures:
            try:
                key, headlines = future.result(timeout=30)
                categories[key] = headlines
            except Exception as e:
                key = futures[future]
                logger.warning(f"Pre-fetch {key} timed out: {e}")
                categories[key] = []

    # Format into compact briefing text
    today = date.today().strftime("%d %B %Y")
    sections = []
    total_headlines = 0
    for key, spec in _STANDARD_QUERIES.items():
        headlines = categories.get(key, [])
        if headlines:
            label = spec["label"]
            section_lines = [f"  [{label}]"]
            for h in headlines[:3]:
                section_lines.append(f"    • {h}")
            sections.append("\n".join(section_lines))
            total_headlines += len(headlines[:3])

    if sections:
        text = f"MARKET BRIEFING ({today}):\n" + "\n".join(sections)
    else:
        text = ""

    elapsed = round(time.time() - t0, 1)
    logger.info(f"Market pre-fetch done: {total_headlines} headlines, "
                f"{len(text)} chars in {elapsed}s")

    with _prefetch_lock:
        _prefetch_cache["text"] = text
        _prefetch_cache["ts"] = time.time()
        _prefetch_cache["categories"] = categories


def _prefetch_loop():
    """Background loop: fetch once, then refresh every hour."""
    while True:
        try:
            _run_prefetch()
        except Exception as e:
            logger.error(f"Pre-fetch loop error: {e}")
        # Sleep for 1 hour before refreshing
        time.sleep(_PREFETCH_TTL)


def start_prefetch():
    """Start the background pre-fetch thread (called once at server startup).

    Thread is daemon=True so it dies with the main process.
    Safe to call multiple times — only starts once.
    """
    global _prefetch_thread
    if _prefetch_thread is not None and _prefetch_thread.is_alive():
        logger.info("Pre-fetch thread already running")
        return

    _prefetch_thread = threading.Thread(
        target=_prefetch_loop,
        name="market-prefetch",
        daemon=True,
    )
    _prefetch_thread.start()
    logger.info("Market pre-fetch background thread started")


def get_market_briefing() -> str:
    """Get the pre-cached market briefing.

    Returns cached text if fresh (< 1 hour old), empty string otherwise.
    This is O(1) — no network calls, no waiting.
    """
    with _prefetch_lock:
        if _prefetch_cache["text"] and (time.time() - _prefetch_cache["ts"]) < _PREFETCH_TTL:
            return _prefetch_cache["text"]
    return ""


def is_prefetch_ready() -> bool:
    """Check if pre-fetched data is available."""
    with _prefetch_lock:
        return bool(_prefetch_cache["text"] and
                    (time.time() - _prefetch_cache["ts"]) < _PREFETCH_TTL)


def get_market_snapshot_cached() -> dict | None:
    """Get a structured market snapshot from live APIs.
    Returns cached data if fresh, None otherwise.
    The ticker bar calls this for instant data."""
    from tools.live_market import get_market_snapshot, _cache, _cache_lock

    # Check if live_market has cached data (any key with a fresh timestamp)
    with _cache_lock:
        if _cache:
            # At least some data is cached — return full snapshot
            # (get_market_snapshot will use cached values internally)
            pass
        else:
            return None

    try:
        return get_market_snapshot()
    except Exception:
        return None
