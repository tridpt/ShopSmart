"""
Tool: Web Search — Tim kiem san pham tren cac san TMDT Viet Nam.
Uses DuckDuckGo search with site-specific queries for Vietnamese e-commerce.
"""
import json
import re
import traceback
from ddgs import DDGS


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


def _extract_prices_from_text(text: str) -> list[float]:
    """Extract VND prices from text using common patterns."""
    prices = []
    if not text:
        return prices

    # Pattern: 1.234.567đ or 1,234,567đ or 1.234.567 VND
    patterns = [
        r'(\d{1,3}(?:\.\d{3})+)\s*(?:đ|₫|VND|vnđ|dong)',
        r'(\d{1,3}(?:,\d{3})+)\s*(?:đ|₫|VND|vnđ|dong)',
        r'(\d{1,3}(?:\.\d{3})+)(?:\s|$)',
        # Pattern: 25tr, 25.9tr (triệu)
        r'(\d+(?:[.,]\d+)?)\s*(?:tr(?:iệu)?|trieu)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                cleaned = match.replace('.', '').replace(',', '')
                value = float(cleaned)
                # Check if it was in "trieu" (millions)
                if 'tr' in pattern.lower():
                    value = value * 1_000_000
                # Sanity check: reasonable price range (10k - 500M VND)
                if 10_000 <= value <= 500_000_000:
                    prices.append(value)
            except (ValueError, TypeError):
                continue

    return prices


def _clean_title(title: str) -> str:
    """Clean up product title from search results."""
    # Remove common suffixes/prefixes
    removals = [
        r'\s*[-|]\s*Shopee\s*.*$',
        r'\s*[-|]\s*Tiki\s*.*$',
        r'\s*[-|]\s*Lazada\s*.*$',
        r'\s*[-|]\s*FPT\s*.*$',
        r'\s*[-|]\s*CellphoneS\s*.*$',
        r'\s*[-|]\s*Thế Giới Di Động\s*.*$',
        r'\s*[-|]\s*Điện máy XANH\s*.*$',
        r'Mua\s+',
        r'\s*Chính Hãng.*$',
        r'\s*Giá Tốt.*$',
    ]
    for pattern in removals:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    return title.strip()


def _identify_source(url: str) -> str:
    """Identify the e-commerce source from URL."""
    for site in ECOMMERCE_SITES:
        if site["domain"] in url:
            return site["name"]
    return "Web"


def search_product(query: str, max_results: int = 10) -> str:
    """
    Tim kiem san pham tren cac san thuong mai dien tu Viet Nam.
    Tra ve danh sach san pham voi ten, gia, link, nguon.

    Args:
        query: Ten san pham can tim (vd: "iPhone 16 128GB")
        max_results: So luong ket qua toi da

    Returns:
        JSON string chua danh sach ket qua tim kiem
    """
    try:
        all_results = []

        # Strategy 1: Search on specific e-commerce sites
        site_queries = [
            f"{query} giá site:shopee.vn OR site:tiki.vn OR site:cellphones.com.vn",
            f"{query} giá site:fptshop.com.vn OR site:thegioididong.com OR site:lazada.vn",
        ]

        with DDGS() as ddgs:
            for sq in site_queries:
                try:
                    results = list(ddgs.text(sq, region="vn-vi", max_results=6))
                    for r in results:
                        url = r.get("href", "")
                        title = r.get("title", "")
                        snippet = r.get("body", "")

                        # Extract price from title + snippet
                        combined_text = f"{title} {snippet}"
                        prices = _extract_prices_from_text(combined_text)
                        price = min(prices) if prices else None

                        source = _identify_source(url)
                        clean = _clean_title(title)

                        if clean:
                            all_results.append({
                                "product_name": clean,
                                "price": price,
                                "price_formatted": f"{price:,.0f}d".replace(",", ".") if price else None,
                                "url": url,
                                "source": source,
                                "snippet": snippet[:150],
                            })
                except Exception:
                    continue

            # Strategy 2: General search if not enough results
            if len(all_results) < 3:
                try:
                    general = list(ddgs.text(
                        f"{query} mua giá bao nhiêu",
                        region="vn-vi",
                        max_results=6
                    ))
                    for r in general:
                        url = r.get("href", "")
                        title = r.get("title", "")
                        snippet = r.get("body", "")

                        prices = _extract_prices_from_text(f"{title} {snippet}")
                        price = min(prices) if prices else None
                        source = _identify_source(url)
                        clean = _clean_title(title)

                        # Avoid duplicates
                        existing_urls = {x["url"] for x in all_results}
                        if clean and url not in existing_urls:
                            all_results.append({
                                "product_name": clean,
                                "price": price,
                                "price_formatted": f"{price:,.0f}d".replace(",", ".") if price else None,
                                "url": url,
                                "source": source,
                                "snippet": snippet[:150],
                            })
                except Exception:
                    pass

        # Sort: products with prices first, then by price ascending
        with_price = sorted(
            [r for r in all_results if r["price"]],
            key=lambda x: x["price"]
        )
        without_price = [r for r in all_results if not r["price"]]
        sorted_results = (with_price + without_price)[:max_results]

        if not sorted_results:
            return json.dumps({
                "success": True,
                "query": query,
                "total_results": 0,
                "results": [],
                "message": f"Khong tim thay ket qua cho '{query}'. Thu tu khoa khac."
            }, ensure_ascii=False)

        # Summary
        prices_found = [r["price"] for r in sorted_results if r["price"]]
        summary = {}
        if prices_found:
            summary = {
                "lowest_price": min(prices_found),
                "highest_price": max(prices_found),
                "lowest_formatted": f"{min(prices_found):,.0f}d".replace(",", "."),
                "highest_formatted": f"{max(prices_found):,.0f}d".replace(",", "."),
                "sources_found": list(set(r["source"] for r in sorted_results)),
            }

        return json.dumps({
            "success": True,
            "query": query,
            "total_results": len(sorted_results),
            "price_summary": summary,
            "results": sorted_results,
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
    "description": "Tim kiem san pham tren cac san thuong mai dien tu Viet Nam (Shopee, Tiki, Lazada, CellphoneS, FPT Shop, TGDD). Tra ve danh sach san pham voi gia, link mua hang, va nguon ban.",
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
