"""Web search tools using DuckDuckGo (no API key needed).

Includes retry logic with exponential backoff to handle 403 rate-limits,
a thread-safe rate limiter, result caching, and cooldown between requests.
"""
import re
import time
import random
import logging
import hashlib
import threading
from ddgs import DDGS

logger = logging.getLogger("financegpt.tools.web")

# ── Thread-safe rate limiter: enforce minimum gap between DuckDuckGo requests ──
_ddgs_lock = threading.Lock()
_last_request_ts: float = 0.0
_MIN_REQUEST_GAP: float = 0.3  # seconds between requests (DuckDuckGo handles moderate concurrency)

# ── Simple result cache (avoid re-fetching identical queries) ──
_cache_lock = threading.Lock()
_search_cache: dict = {}       # key → (result, timestamp)
_CACHE_TTL: int = 600          # 10 minutes

# ── Cached world briefing (fetched once per hour) ──
_world_briefing_cache: dict = {"text": "", "ts": 0}
_briefing_lock = threading.Lock()


def _rate_limit():
    """Enforce minimum gap between DuckDuckGo requests (thread-safe)."""
    global _last_request_ts
    with _ddgs_lock:
        elapsed = time.time() - _last_request_ts
        if elapsed < _MIN_REQUEST_GAP:
            sleep_time = _MIN_REQUEST_GAP - elapsed + random.uniform(0.1, 0.5)
            time.sleep(sleep_time)
        _last_request_ts = time.time()


def _cache_key(func_name: str, query: str) -> str:
    return hashlib.md5(f"{func_name}:{query}".encode()).hexdigest()


def _get_cached(key: str):
    with _cache_lock:
        if key in _search_cache:
            result, ts = _search_cache[key]
            if time.time() - ts < _CACHE_TTL:
                return result
            del _search_cache[key]
        return None


def _set_cached(key: str, result):
    with _cache_lock:
        _search_cache[key] = (result, time.time())
        # Evict old entries if cache grows too large
        if len(_search_cache) > 100:
            oldest_key = min(_search_cache, key=lambda k: _search_cache[k][1])
            del _search_cache[oldest_key]


def _ddgs_with_retry(func_name: str, query: str, max_results: int = 5,
                     max_retries: int = 3) -> list:
    """Execute a DDGS search with retry + exponential backoff.

    func_name: 'text' or 'news'
    Returns list of result dicts, or empty list on failure.
    """
    ck = _cache_key(func_name, f"{query}:{max_results}")
    cached = _get_cached(ck)
    if cached is not None:
        return cached

    for attempt in range(max_retries):
        try:
            _rate_limit()
            with DDGS() as ddgs:
                fn = getattr(ddgs, func_name)
                results = list(fn(query, max_results=max_results))
            if results:
                _set_cached(ck, results)
            return results
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "403" in err_str or "ratelimit" in err_str
            is_decode = "decode" in err_str
            is_timeout = "timeout" in err_str

            if is_rate_limit or is_decode or is_timeout:
                wait = (2 ** attempt) + random.uniform(0.5, 2.0)
                logger.warning(
                    f"DDGS {func_name} attempt {attempt+1}/{max_retries} "
                    f"failed ({type(e).__name__}), retrying in {wait:.1f}s"
                )
                time.sleep(wait)
            else:
                logger.error(f"DDGS {func_name} non-retryable error: {e}")
                return []
    logger.error(f"DDGS {func_name} failed after {max_retries} retries for: {query[:60]}")
    return []
_BRIEFING_TTL = 3600  # 1 hour

# Words to strip from user queries before building a web search
_STOP_WORDS = {
    "i", "me", "my", "am", "is", "are", "was", "were", "be", "been",
    "a", "an", "the", "and", "or", "but", "if", "so", "as", "at", "by",
    "to", "in", "on", "of", "for", "it", "its", "do", "did", "does",
    "has", "had", "have", "can", "could", "will", "would", "should",
    "shall", "may", "might", "must", "being", "this", "that", "these",
    "those", "what", "which", "who", "whom", "how", "when", "where",
    "why", "not", "no", "nor", "also", "just", "about", "with",
    "from", "into", "than", "then", "very", "too", "more", "most",
    "some", "any", "all", "each", "every", "both", "few", "other",
    "such", "only", "own", "same", "up", "out", "off", "over", "under",
    "again", "here", "there", "once", "please", "help", "tell", "know",
    "want", "need", "like", "think", "give", "make", "get", "let",
    "much", "many", "well", "good", "right", "now", "still", "old",
    "new", "year", "years", "month", "months", "today", "currently",
    "really", "already", "going", "been", "being", "having",
}


def query_to_search(query: str, suffix: str = "") -> str:
    """Convert a user's natural language question into a clean web search query.
    Keeps ALL meaningful words (events, names, places, financial terms).
    Only strips filler/stop words. Preserves capitalized proper nouns.
    """
    # First, extract capitalized proper nouns/names before lowering
    _proper_raw = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
    proper_nouns = []
    for phrase in _proper_raw:
        for word in phrase.lower().split():
            if word not in _STOP_WORDS and len(word) > 1:
                proper_nouns.append(word)

    q = query.lower().strip()
    # Remove amounts/numbers like "25 lakhs", "₹50000", "32 years old"
    q = re.sub(r'₹?\d[\d,]*\.?\d*\s*(?:lakhs?|lacs?|crores?|cr|lpa|[lkc])?\b', '', q)
    q = re.sub(r'\b\d+\s*(?:years?\s*old|yrs?\s*old)\b', '', q)
    q = re.sub(r'\b\d{1,2}\s*(?:lpa|ctc)\b', '', q)
    # Keep meaningful words
    words = re.findall(r'[a-z]+', q)
    keywords = [w for w in words if w not in _STOP_WORDS and len(w) > 1]
    # Ensure proper nouns are included even if they look like stop words
    for pn in proper_nouns:
        pn_words = pn.split()
        for pw in pn_words:
            if pw not in keywords:
                keywords.insert(0, pw)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    result = " ".join(unique[:10])
    if suffix:
        result = f"{result} {suffix}".strip()
    return result if result else "India financial news"


def query_web_context(query: str) -> str:
    """Do a query-driven web search to give the LLM current context.
    Combines news + text results for the user's actual question,
    returning substantive snippets (not just headlines).
    Uses retry-backed searches with rate limiting.
    """
    search_q = query_to_search(query, "India 2025 2026")
    logger.info(f"Query web context: '{search_q}'")

    parts = []

    # News results for recency
    news = _ddgs_with_retry("news", search_q, max_results=3)
    for r in news[:3]:
        title = r.get("title", "").strip()
        body = r.get("body", "").strip()
        source = r.get("source", "").strip()
        if title:
            line = f"[{source}] {title}"
            if body:
                line += f": {body[:150]}"
            parts.append(line)

    # Text results for depth
    texts = _ddgs_with_retry("text", search_q, max_results=3)
    for r in texts[:3]:
        title = r.get("title", "").strip()
        snippet = r.get("body", "").strip()
        if title and snippet:
            parts.append(f"{title}: {snippet[:200]}")

    if not parts:
        return ""

    text = "CURRENT INFORMATION (web search results):\n" + "\n".join(f"  • {p}" for p in parts[:5])
    logger.info(f"Query web context: {len(parts)} results, {len(text)} chars")
    return text


def get_world_briefing() -> str:
    """Return a compact financial world briefing, cached for 1 hour (thread-safe).
    Fetches top headlines + snippets on India economy, global markets, and RBI/SEBI.
    ~600-900 chars — small enough to always fit in context.
    """
    now = time.time()
    with _briefing_lock:
        if _world_briefing_cache["text"] and (now - _world_briefing_cache["ts"]) < _BRIEFING_TTL:
            return _world_briefing_cache["text"]

    queries = [
        "India economy stock market today",
        "global markets US economy tariff trade news today",
    ]
    headlines = []
    for q in queries:
        results = _ddgs_with_retry("news", q, max_results=4)
        for r in results:
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            source = r.get("source", "").strip()
            if title and title not in [h.split("] ", 1)[-1].split(":")[0] for h in headlines]:
                line = f"[{source}] {title}"
                if body:
                    line += f": {body[:120]}"
                headlines.append(line)
            if len(headlines) >= 5:
                break
        if len(headlines) >= 5:
            break

    if not headlines:
        return ""

    from datetime import date
    today = date.today().strftime("%d %B %Y")
    text = f"TODAY'S WORLD ({today}):\n" + "\n".join(f"  • {h}" for h in headlines[:5])
    logger.info(f"World briefing fetched: {len(headlines)} headlines, {len(text)} chars")

    with _briefing_lock:
        _world_briefing_cache["text"] = text
        _world_briefing_cache["ts"] = now
    return text


def web_search(query: str, max_results: int = 5) -> list:
    """Search the web and return results."""
    logger.info(f"Web search: {query[:80]}")
    results = _ddgs_with_retry("text", query, max_results=max_results)
    logger.info(f"Web search returned {len(results)} results")
    return [
        {
            "title": r.get("title", ""),
            "snippet": r.get("body", ""),
            "url": r.get("href", ""),
        }
        for r in results
    ] if results else [{"error": "No results found"}]


def news_search(query: str, max_results: int = 5) -> list:
    """Search for recent news articles."""
    logger.info(f"News search: {query[:80]}")
    results = _ddgs_with_retry("news", query, max_results=max_results)
    logger.info(f"News search returned {len(results)} results")
    return [
        {
            "title": r.get("title", ""),
            "snippet": r.get("body", ""),
            "url": r.get("url", ""),
            "date": r.get("date", ""),
            "source": r.get("source", ""),
        }
        for r in results
    ] if results else [{"error": "No results found"}]


def financial_news(topic: str = "stock market") -> list:
    """Get latest financial news."""
    return news_search(f"{topic} financial news today")


def search_financial_term(term: str) -> list:
    """Look up a financial term or concept."""
    return web_search(f"{term} financial definition explanation")


def search_stock_news(ticker: str) -> list:
    """Get latest news for a specific stock."""
    return news_search(f"{ticker} stock news analysis")


def search_regulation(topic: str) -> list:
    """Search for financial regulations and compliance info."""
    return web_search(f"{topic} financial regulation rules 2024 2025")


def search_tax_update(topic: str) -> list:
    """Search for latest tax law updates."""
    return web_search(f"{topic} tax law update 2024 2025")
