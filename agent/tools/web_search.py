"""
Tool: Web Search — Tim kiem san pham tren cac san TMDT Viet Nam.
Uses DuckDuckGo search with site-specific queries for Vietnamese e-commerce.
"""
import json
import os
import re
import traceback
from ddgs import DDGS

from agent.tools.cache_util import TTLCache, RateLimiter


# Cache search results for a short while so repeated/identical queries don't
# re-hit DuckDuckGo, and rate-limit outbound calls to avoid HTTP 429 blocks.
_SEARCH_TTL = float(os.environ.get("SEARCH_CACHE_TTL", "300"))      # 5 minutes
_SEARCH_MAX_CALLS = int(os.environ.get("SEARCH_RATE_MAX_CALLS", "8"))
_SEARCH_PERIOD = float(os.environ.get("SEARCH_RATE_PERIOD", "60"))   # per 60s

_search_cache = TTLCache(ttl=_SEARCH_TTL, max_entries=256)
_rate_limiter = RateLimiter(max_calls=_SEARCH_MAX_CALLS, period=_SEARCH_PERIOD)


# Vietnamese e-commerce sites to search
ECOMMERCE_SITES = [
    {"name": "Shopee", "domain": "shopee.vn", "icon": "shopee"},
    {"name": "Tiki", "domain": "tiki.vn", "icon": "tiki"},
    {"name": "CellphoneS", "domain": "cellphones.com.vn", "icon": "cellphones"},
    {"name": "FPT Shop", "domain": "fptshop.com.vn", "icon": "fptshop"},
    {"name": "Lazada", "domain": "lazada.vn", "icon": "lazada"},
    {"name": "The Gioi Di Dong", "domain": "thegioididong.com", "icon": "tgdd"},
    {"name": "Dien May Xanh", "domain": "dienmayxanh.com", "icon": "dmx"},
    {"name": "Hnam Mobile", "domain": "hnammobile.com", "icon": "hnam"},
]

# Snippets to filter out (useless descriptions)
_BAD_SNIPPETS = [
    "we cannot provide a description for this page right now",
    "we can't provide a description for this page right now",
    "không thể cung cấp mô tả cho trang này",
]


def _clean_title(title: str) -> str:
    """Clean up product title from search results."""
    removals = [
        r'\s*[-|–]\s*Shopee\s*.*$',
        r'\s*[-|–]\s*Tiki\s*.*$',
        r'\s*[-|–]\s*Lazada\s*.*$',
        r'\s*[-|–]\s*FPT\s*.*$',
        r'\s*[-|–]\s*CellphoneS\s*.*$',
        r'\s*[-|–]\s*Thế Giới Di Động\s*.*$',
        r'\s*[-|–]\s*Điện máy XANH\s*.*$',
        r'\s*[-|–]\s*Hnam\s*.*$',
        r'^Mua\s+',
        r'\s*Chính Hãng\s*$',
        r'\s*Giá Tốt\s*$',
        r'\s*[-|–]\s*$',  # Remove trailing dash
    ]
    for pattern in removals:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    return title.strip().rstrip('-–|').strip()


def _clean_snippet(snippet: str) -> str:
    """Clean snippet, remove useless descriptions."""
    if not snippet:
        return ""
    snippet_lower = snippet.lower().strip()
    for bad in _BAD_SNIPPETS:
        if bad in snippet_lower:
            return ""
    return snippet.strip()


def _identify_source(url: str) -> str:
    """Identify the e-commerce source from URL."""
    for site in ECOMMERCE_SITES:
        if site["domain"] in url:
            return site["name"]
    return "Web"


def search_product(query: str, max_results: int = 10) -> str:
    """
    Tim kiem san pham tren cac san thuong mai dien tu Viet Nam.
    Tra ve danh sach san pham voi ten, link, nguon ban.

    Args:
        query: Ten san pham can tim (vd: "iPhone 16 128GB")
        max_results: So luong ket qua toi da

    Returns:
        JSON string chua danh sach ket qua tim kiem
    """
    query = (query or "").strip()
    if not query:
        return json.dumps({
            "success": False,
            "message": "Vui long nhap tu khoa tim kiem.",
            "results": []
        }, ensure_ascii=False)

    # 1) Serve from cache when possible (keyed by normalized query + max_results).
    cache_key = f"{query.lower()}::{max_results}"
    cached = _search_cache.get(cache_key)
    if cached is not None:
        return cached

    # 2) Rate-limit outbound search calls to avoid being blocked (HTTP 429).
    if not _rate_limiter.acquire():
        retry_after = round(_rate_limiter.time_until_next(), 1)
        # If we have a stale cached entry, prefer returning it over an error.
        stale = _search_cache.get(cache_key, allow_stale=True)
        if stale is not None:
            return stale
        return json.dumps({
            "success": False,
            "query": query,
            "rate_limited": True,
            "message": f"Dang tim kiem qua nhanh. Vui long thu lai sau {retry_after}s.",
            "results": []
        }, ensure_ascii=False)

    result_json = _do_search(query, max_results)

    # 3) Only cache successful, non-empty responses.
    try:
        parsed = json.loads(result_json)
        if parsed.get("success") and parsed.get("total_results", 0) > 0:
            _search_cache.set(cache_key, result_json)
    except (json.JSONDecodeError, TypeError):
        pass

    return result_json


def _do_search(query: str, max_results: int = 10) -> str:
    """Perform the actual DuckDuckGo search (no caching/rate-limiting)."""
    try:
        all_results = []
        seen_urls = set()

        # Strategy 1: Search on specific e-commerce sites
        site_queries = [
            f"{query} site:shopee.vn OR site:tiki.vn OR site:cellphones.com.vn",
            f"{query} site:fptshop.com.vn OR site:thegioididong.com OR site:lazada.vn",
        ]

        with DDGS() as ddgs:
            for sq in site_queries:
                try:
                    results = list(ddgs.text(sq, region="vn-vi", max_results=8))
                    for r in results:
                        url = r.get("href", "")
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)

                        title = r.get("title", "")
                        snippet = r.get("body", "")

                        source = _identify_source(url)
                        clean_name = _clean_title(title)
                        clean_snip = _clean_snippet(snippet)

                        if clean_name and source != "Web":
                            all_results.append({
                                "product_name": clean_name,
                                "url": url,
                                "source": source,
                                "snippet": clean_snip[:160] if clean_snip else None,
                            })
                except Exception:
                    continue

            # Strategy 2: General search if not enough results
            if len(all_results) < 4:
                try:
                    general = list(ddgs.text(
                        f"{query} mua ở đâu",
                        region="vn-vi",
                        max_results=6
                    ))
                    for r in general:
                        url = r.get("href", "")
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)

                        title = r.get("title", "")
                        snippet = r.get("body", "")

                        source = _identify_source(url)
                        clean_name = _clean_title(title)
                        clean_snip = _clean_snippet(snippet)

                        if clean_name:
                            all_results.append({
                                "product_name": clean_name,
                                "url": url,
                                "source": source,
                                "snippet": clean_snip[:160] if clean_snip else None,
                            })
                except Exception:
                    pass

        # Limit results
        final_results = all_results[:max_results]

        if not final_results:
            return json.dumps({
                "success": True,
                "query": query,
                "total_results": 0,
                "results": [],
                "message": f"Khong tim thay ket qua cho '{query}'. Thu tu khoa khac."
            }, ensure_ascii=False)

        return json.dumps({
            "success": True,
            "query": query,
            "total_results": len(final_results),
            "sources_found": list(set(r["source"] for r in final_results)),
            "results": final_results,
        }, ensure_ascii=False)

    except Exception as e:
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "message": f"Loi khi tim kiem: {str(e)}",
            "results": []
        }, ensure_ascii=False)


# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "name": "search_product",
    "description": "Tim kiem san pham tren cac san thuong mai dien tu Viet Nam (Shopee, Tiki, Lazada, CellphoneS, FPT Shop, TGDD). Tra ve danh sach san pham voi link mua hang va nguon ban.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Ten san pham hoac tu khoa tim kiem"
            },
            "max_results": {
                "type": "integer",
                "description": "So luong ket qua toi da (mac dinh 10)"
            }
        },
        "required": ["query"]
    }
}
