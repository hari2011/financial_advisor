"""Deep web research module — multi-query search + page extraction + citations.

Brings Gemini/Perplexity-style grounded responses to the local LLM:
  1. Decompose user query → 2-3 search sub-queries
  2. Search each sub-query via DuckDuckGo (with retry)
  3. Fetch top URLs → extract readable article text
  4. Rank and select best passages within token budget
  5. Format as numbered sources with URLs for LLM citation
"""

import re
import time
import logging
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    import trafilatura
    _HAS_TRAFILATURA = True
except ImportError:
    _HAS_TRAFILATURA = False

from tools.web_search import _ddgs_with_retry, query_to_search

logger = logging.getLogger("financegpt.tools.deep_research")

# ── Cache for extracted pages (avoid re-fetching same URL) ──
_page_cache: dict = {}       # url → (text, timestamp)
_PAGE_CACHE_TTL: int = 900   # 15 minutes

# ── Domains to skip (paywalls, login-walls, useless) ──
_BLOCKED_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "pinterest.com", "tiktok.com",
    "youtube.com", "reddit.com",  # video/forum — not article text
}

# ── Research result cache ──
_research_cache: dict = {}
_RESEARCH_CACHE_TTL: int = 600  # 10 minutes


# ─────────────────────────────────────────────────────────────────
# 1. QUERY DECOMPOSITION
# ─────────────────────────────────────────────────────────────────

def decompose_query(query: str) -> list[str]:
    """Break a user question into 1-2 focused search sub-queries.

    Uses rule-based decomposition (fast, no LLM call needed):
    - Base query: direct factual search
    - Domain-specific angle (analysis/rules/comparison)

    NOTE: "latest news" sub-query removed — standard market news is now
    pre-fetched hourly by market_prefetch.py and injected into context.
    This reduces DuckDuckGo calls from 3 to 2, cutting deep_research
    latency by ~30% and avoiding rate-limit failures on news queries.
    """
    base = query_to_search(query, "")
    if not base or len(base.split()) < 2:
        base = query.strip()[:80]

    sub_queries = []

    # Sub-query 1: Direct factual search
    sub_queries.append(f"{base} India 2025 2026")

    # Sub-query 2: Domain-specific analysis angle
    q_lower = query.lower()
    if any(w in q_lower for w in ["stock", "share", "invest", "buy", "sell", "nifty", "sensex"]):
        sub_queries.append(f"{base} analysis outlook forecast")
    elif any(w in q_lower for w in ["tax", "itr", "80c", "deduction", "regime"]):
        sub_queries.append(f"{base} rules changes latest")
    elif any(w in q_lower for w in ["loan", "emi", "interest", "rate"]):
        sub_queries.append(f"{base} interest rate comparison best")
    elif any(w in q_lower for w in ["mutual fund", "sip", "elss", "etf"]):
        sub_queries.append(f"{base} performance review recommendation")
    else:
        sub_queries.append(f"{base} expert analysis India")

    return sub_queries[:2]


# ─────────────────────────────────────────────────────────────────
# 2. MULTI-SOURCE SEARCH
# ─────────────────────────────────────────────────────────────────

def _search_multiple_queries(sub_queries: list[str],
                             results_per_query: int = 4) -> list[dict]:
    """Search DuckDuckGo for each sub-query IN PARALLEL, deduplicate by URL."""
    all_results = []
    seen_urls = set()
    _results_lock = threading.Lock()

    def _add_result(r, is_news=False, sq=""):
        url = r.get("href" if not is_news else "url", "")
        if not url:
            return
        domain = urlparse(url).netloc.replace("www.", "")
        if domain in _BLOCKED_DOMAINS:
            return
        with _results_lock:
            if url in seen_urls:
                return
            seen_urls.add(url)
        entry = {
            "title": r.get("title", "").strip(),
            "snippet": r.get("body", "").strip(),
            "url": url,
            "domain": domain,
            "query": sq,
        }
        if is_news:
            entry["source"] = r.get("source", "")
            entry["is_news"] = True
        with _results_lock:
            all_results.append(entry)

    def _search_text(sq):
        results = _ddgs_with_retry("text", sq, max_results=results_per_query)
        for r in results:
            _add_result(r, sq=sq)

    def _search_news(sq):
        results = _ddgs_with_retry("news", sq, max_results=3)
        for r in results:
            _add_result(r, is_news=True, sq=sq)

    # Run ALL searches in parallel: text for first query + news for the rest
    import threading as _thr
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="ddgs") as pool:
        futures = []
        futures.append(pool.submit(_search_text, sub_queries[0]))
        for sq in sub_queries[1:]:
            futures.append(pool.submit(_search_news, sq))
        for f in futures:
            try:
                f.result(timeout=30)
            except Exception as e:
                logger.warning(f"Parallel search task failed: {e}")

    logger.info(f"Multi-search: {len(sub_queries)} queries → {len(all_results)} unique results")
    return all_results


# ─────────────────────────────────────────────────────────────────
# 3. WEBPAGE CONTENT EXTRACTION
# ─────────────────────────────────────────────────────────────────

_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _extract_page_text(url: str, max_chars: int = 3000) -> str:
    """Fetch a URL and extract the main article text.

    Primary: trafilatura (purpose-built for article extraction).
    Fallback: BeautifulSoup heuristic parsing.
    Returns cleaned text up to max_chars, or empty string on failure.
    """
    # Check cache
    if url in _page_cache:
        text, ts = _page_cache[url]
        if time.time() - ts < _PAGE_CACHE_TTL:
            return text[:max_chars]
        del _page_cache[url]

    try:
        resp = requests.get(url, headers=_REQUEST_HEADERS, timeout=8,
                            allow_redirects=True)
        resp.raise_for_status()

        # Only process HTML
        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type:
            return ""

        html = resp.text
        result = ""

        # Primary: trafilatura
        if _HAS_TRAFILATURA:
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
            )
            if extracted:
                result = extracted[:max_chars]

        # Fallback: BeautifulSoup
        if not result:
            soup = BeautifulSoup(html, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header",
                             "aside", "form", "iframe", "noscript",
                             "figure", "figcaption", "svg", "button"]):
                tag.decompose()

            article = (
                soup.find("article") or
                soup.find("main") or
                soup.find("div", class_=re.compile(
                    r"article|content|post|entry|story", re.I)) or
                soup.find("div", id=re.compile(
                    r"article|content|post|entry|story", re.I))
            )

            paragraphs = (article.find_all("p") if article
                          else soup.find_all("p"))

            texts = []
            total_len = 0
            for p in paragraphs:
                t = p.get_text(separator=" ", strip=True)
                if len(t) < 40:
                    continue
                if any(skip in t.lower() for skip in [
                    "cookie", "subscribe", "sign up", "newsletter",
                    "accept all", "privacy policy", "terms of use"
                ]):
                    continue
                texts.append(t)
                total_len += len(t)
                if total_len >= max_chars:
                    break

            result = "\n".join(texts)[:max_chars]

        # Cache it
        if result:
            _page_cache[url] = (result, time.time())
            if len(_page_cache) > 50:
                oldest = min(_page_cache, key=lambda k: _page_cache[k][1])
                del _page_cache[oldest]

        return result

    except Exception as e:
        logger.debug(f"Page extraction failed for {url}: {e}")
        return ""


def _fetch_pages_parallel(results: list[dict], max_pages: int = 5,
                          max_chars_per_page: int = 1500) -> list[dict]:
    """Fetch and extract text from top URLs in parallel."""
    to_fetch = results[:max_pages]
    enriched = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_result = {
            executor.submit(_extract_page_text, r["url"], max_chars_per_page): r
            for r in to_fetch
        }
        for future in as_completed(future_to_result):
            r = future_to_result[future]
            try:
                page_text = future.result()
                r["page_text"] = page_text
            except Exception:
                r["page_text"] = ""
            enriched.append(r)

    # Sort: results with extracted text first, then by original order
    enriched.sort(key=lambda x: (len(x.get("page_text", "")) == 0,
                                  results.index(x) if x in results else 999))
    return enriched


# ─────────────────────────────────────────────────────────────────
# 4. PASSAGE RANKING & BUDGET-AWARE SELECTION
# ─────────────────────────────────────────────────────────────────

def _score_result(result: dict, query_words: set) -> float:
    """Score a search result by relevance to the query."""
    score = 0.0
    title = result.get("title", "").lower()
    snippet = result.get("snippet", "").lower()
    page_text = result.get("page_text", "").lower()

    # Word overlap with title (high signal)
    title_words = set(title.split())
    score += len(query_words & title_words) * 3.0

    # Word overlap with snippet
    snippet_words = set(snippet.split())
    score += len(query_words & snippet_words) * 1.5

    # Has extracted page text (major bonus)
    if page_text:
        score += 5.0
        # Check for financial data markers in page text
        if any(marker in page_text for marker in [
            "₹", "crore", "lakh", "nifty", "sensex", "nse", "bse",
            "p/e", "earnings", "revenue", "growth", "dividend",
            "rbi", "sebi", "gst", "income tax",
        ]):
            score += 3.0

    # News recency bonus
    if result.get("is_news"):
        score += 2.0

    # Trusted financial domains bonus
    domain = result.get("domain", "")
    trusted = [
        "moneycontrol.com", "livemint.com", "economictimes.com",
        "screener.in", "tickertape.in", "valueresearchonline.com",
        "cleartax.in", "paisabazaar.com", "bankbazaar.com",
        "ndtv.com", "reuters.com", "bloomberg.com",
        "investopedia.com", "morningstar.com",
    ]
    if any(t in domain for t in trusted):
        score += 4.0

    return score


def _select_within_budget(results: list[dict], query: str,
                          max_chars: int = 8000) -> list[dict]:
    """Rank results and select the best ones that fit within budget."""
    query_words = set(query.lower().split())
    query_words -= {"i", "the", "a", "is", "are", "to", "in", "for", "of", "my"}

    # Score and sort
    for r in results:
        r["_score"] = _score_result(r, query_words)
    results.sort(key=lambda x: x["_score"], reverse=True)

    selected = []
    total_chars = 0
    for r in results:
        # Estimate size of this source in final context
        text = r.get("page_text") or r.get("snippet", "")
        entry_size = len(r.get("title", "")) + len(text) + len(r.get("url", "")) + 50
        if total_chars + entry_size > max_chars:
            # Try with just snippet if page text is too large
            if r.get("page_text") and total_chars + 300 < max_chars:
                r["page_text"] = ""  # Fall back to snippet
                entry_size = len(r.get("title", "")) + len(r.get("snippet", "")) + 80
                if total_chars + entry_size <= max_chars:
                    selected.append(r)
                    total_chars += entry_size
            continue
        selected.append(r)
        total_chars += entry_size
        if len(selected) >= 8:  # Cap at 8 sources
            break

    return selected


# ─────────────────────────────────────────────────────────────────
# 5. FORMAT WITH CITATIONS
# ─────────────────────────────────────────────────────────────────

def _format_cited_context(sources: list[dict]) -> str:
    """Format sources as numbered citations for LLM consumption.

    Output format:
        WEB SOURCES (cite as [1], [2], etc.):

        [1] Title (domain.com)
        URL: https://...
        Content: extracted text or snippet...

        [2] ...
    """
    if not sources:
        return ""

    lines = [
        "WEB SOURCES (cite as [1], [2], etc. in your response):\n"
    ]

    for i, src in enumerate(sources, 1):
        domain = src.get("domain", "")
        title = src.get("title", "Untitled")
        url = src.get("url", "")
        text = src.get("page_text") or src.get("snippet", "")

        lines.append(f"[{i}] {title} ({domain})")
        lines.append(f"    URL: {url}")
        if text:
            # Trim to reasonable length
            if len(text) > 1000:
                text = text[:1000] + "..."
            lines.append(f"    Content: {text}")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def deep_research(query: str, max_context_chars: int = 5000,
                  search_queries: list[str] | None = None) -> str:
    """Performs deep web research.

    Steps:
      1. Use LLM-generated search queries if provided, else decompose query
      2. Multi-source search (news + text)
      3. Fetch top page content in parallel
      4. Rank, select within budget
      5. Return formatted context with numbered citations

    Args:
        query: User's natural language question
        max_context_chars: Maximum characters for the formatted output
        search_queries: Optional LLM-generated search queries (from router).
                       If provided, skips rule-based decomposition.

    Returns:
        Formatted string with numbered sources and citations,
        or empty string if no useful results found.
    """
    t0 = time.time()

    # Check cache
    ck = hashlib.md5(query.lower().strip().encode()).hexdigest()
    if ck in _research_cache:
        text, ts = _research_cache[ck]
        if time.time() - ts < _RESEARCH_CACHE_TTL:
            logger.info(f"Deep research cache hit ({len(text)} chars)")
            return text

    # Step 1: Get search queries (LLM-generated or rule-based fallback)
    if search_queries:
        sub_queries = search_queries[:3]
        logger.info(f"Deep research: {len(sub_queries)} LLM-generated queries for: {query[:60]}")
    else:
        sub_queries = decompose_query(query)
        logger.info(f"Deep research: {len(sub_queries)} rule-based queries for: {query[:60]}")

    # Step 2: Multi-source search
    results = _search_multiple_queries(sub_queries, results_per_query=4)
    if not results:
        logger.warning("Deep research: no search results")
        return ""

    # Step 3: Fetch page content (parallel)
    enriched = _fetch_pages_parallel(results, max_pages=5, max_chars_per_page=2000)

    # Step 4: Rank and select within budget
    selected = _select_within_budget(enriched, query, max_chars=max_context_chars)
    if not selected:
        logger.warning("Deep research: no sources passed budget filter")
        return ""

    # Step 5: Format with citations
    output = _format_cited_context(selected)

    elapsed = time.time() - t0
    logger.info(f"Deep research: {len(selected)} sources, {len(output)} chars, {elapsed:.1f}s")

    # Cache result
    _research_cache[ck] = (output, time.time())
    if len(_research_cache) > 30:
        oldest = min(_research_cache, key=lambda k: _research_cache[k][1])
        del _research_cache[oldest]

    return output
