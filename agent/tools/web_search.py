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

# Words that indicate a number is NOT a product price
_DISCOUNT_KEYWORDS = [
    'giảm', 'giam', 'tiết kiệm', 'tiet kiem', 'khuyến mãi', 'khuyen mai',
    'ưu đãi', 'uu dai', 'trả góp', 'tra gop', 'hoàn', 'hoan', 'voucher',
    'coupon', 'mã giảm', 'ma giam', 'chiết khấu', 'chiet khau', 'giảm đến',
    'giảm còn', 'giảm liền', 'giảm thêm', 'giảm sốc', 'giảm mạnh',
    'off', 'discount', 'save', 'freeship',
    'trả chậm', 'tra cham', 'tháng', 'thang', '/tháng', 'góp', 'gop',
    'trả trước', 'tra truoc', 'đặt cọc', 'dat coc', 'chỉ từ', 'chi tu',
    'chỉ còn', 'chi con', 'tiền mặt', 'tien mat',
    'bảng giá', 'bang gia', 'cập nhật', 'cap nhat', 'mới nhất', 'moi nhat',
]

# URLs that are blog/article pages (not product pages) — prices are unreliable
_BLOG_URL_PATTERNS = [
    r'/tin-tuc/', r'/bai-viet/', r'/blog/', r'/news/',
    r'/bang-gia', r'/gia-ban', r'/cap-nhat-gia',
    r'/top-\d+', r'/so-sanh', r'/danh-gia', r'/review',
]


def _is_product_page_url(url: str) -> bool:
    """Check if URL is a direct product page (not blog/article)."""
    product_patterns = [
        r'shopee\.vn/.*-i\.\d+\.\d+',           # Shopee product
        r'tiki\.vn/.*p\d+',                       # Tiki product
        r'lazada\.vn/products/',                   # Lazada product
        r'cellphones\.com\.vn/.*\.html',           # CellphoneS product
        r'fptshop\.com\.vn/.+/.*\.html',           # FPT Shop product
        r'thegioididong\.com/.+',                  # TGDD product
        r'dienmayxanh\.com/.+',                    # DMX product
    ]
    for pattern in product_patterns:
        if re.search(pattern, url):
            return True
    return False


def _extract_product_price(text: str) -> float | None:
    """
    Extract the ACTUAL product price from text, filtering out discounts.
    Returns None if no confident price found.
    """
    if not text:
        return None

    text_lower = text.lower()

    # Strategy 1: Look for explicit price patterns like "giá: 25.990.000đ" or "giá từ 25.990.000"
    explicit_patterns = [
        r'giá\s*(?:từ|chỉ|còn|:)?\s*(\d{1,3}(?:\.\d{3})+)\s*(?:đ|₫|VND|vnđ|d)',
        r'giá\s*(?:từ|chỉ|còn|:)?\s*(\d{1,3}(?:\.\d{3})+)',
        r'giá\s*(?:từ|chỉ|còn|:)?\s*(\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|tr)\b',
    ]

    for pattern in explicit_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            price = _parse_price_value(match, 'tr' in pattern.lower())
            if price and _is_reasonable_price(price):
                return price

    # Strategy 2: Look for standalone prices with VND suffix (high confidence)
    vnd_pattern = r'(\d{1,3}(?:\.\d{3}){1,3})\s*(?:đ|₫|VND|vnđ)\b'
    vnd_matches = re.finditer(vnd_pattern, text, re.IGNORECASE)

    valid_prices = []
    for m in vnd_matches:
        price_str = m.group(1)
        # Check surrounding context — is this near a discount word?
        start = max(0, m.start() - 40)
        context_before = text_lower[start:m.start()]

        is_discount = any(kw in context_before for kw in _DISCOUNT_KEYWORDS)
        if is_discount:
            continue

        price = _parse_price_value(price_str, False)
        if price and _is_reasonable_price(price):
            valid_prices.append(price)

    if valid_prices:
        # Return the most likely product price (highest among valid ones,
        # since discounts tend to be smaller numbers)
        return max(valid_prices)

    # Strategy 3: Look for "XX triệu" pattern with context
    tr_pattern = r'(\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|tr)\b'
    tr_matches = re.finditer(tr_pattern, text, re.IGNORECASE)

    for m in tr_matches:
        start = max(0, m.start() - 40)
        context_before = text_lower[start:m.start()]
        is_discount = any(kw in context_before for kw in _DISCOUNT_KEYWORDS)
        if is_discount:
            continue

        price = _parse_price_value(m.group(1), True)
        if price and _is_reasonable_price(price):
            valid_prices.append(price)

    if valid_prices:
        return max(valid_prices)

    return None


def _parse_price_value(price_str: str, is_millions: bool) -> float | None:
    """Parse a price string to float value."""
    try:
        cleaned = price_str.replace('.', '').replace(',', '')
        value = float(cleaned)
        if is_millions:
            # Handle "25" or "25.9" or "259"
            if value < 1000:
                value = value * 1_000_000
        return value
    except (ValueError, TypeError):
        return None


def _is_reasonable_price(price: float) -> bool:
    """Check if a price is in a reasonable range for Vietnamese products."""
    # Min 50,000 VND (~$2), Max 500,000,000 VND (~$20,000)
    return 50_000 <= price <= 500_000_000


def _clean_title(title: str) -> str:
    """Clean up product title from search results."""
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


def _format_price(price: float) -> str:
    """Format price with dots as thousands separator."""
    return f"{price:,.0f}d".replace(",", ".")


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

                        # Skip price extraction for blog/article URLs (prices are unreliable)
                        is_blog = any(re.search(p, url, re.IGNORECASE) for p in _BLOG_URL_PATTERNS)

                        price = None
                        if not is_blog:
                            # Only extract price from snippet (not title — title often has discount amounts)
                            price = _extract_product_price(snippet)

                            # If no price from snippet, try title only for product pages
                            if price is None and _is_product_page_url(url):
                                price = _extract_product_price(title)

                        source = _identify_source(url)
                        clean = _clean_title(title)

                        if clean:
                            all_results.append({
                                "product_name": clean,
                                "price": price,
                                "price_formatted": _format_price(price) if price else None,
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

                        is_blog = any(re.search(p, url, re.IGNORECASE) for p in _BLOG_URL_PATTERNS)
                        price = None
                        if not is_blog:
                            price = _extract_product_price(snippet)
                            if price is None and _is_product_page_url(url):
                                price = _extract_product_price(title)

                        source = _identify_source(url)
                        clean = _clean_title(title)

                        existing_urls = {x["url"] for x in all_results}
                        if clean and url not in existing_urls:
                            all_results.append({
                                "product_name": clean,
                                "price": price,
                                "price_formatted": _format_price(price) if price else None,
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
                "lowest_formatted": _format_price(min(prices_found)),
                "highest_formatted": _format_price(max(prices_found)),
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
