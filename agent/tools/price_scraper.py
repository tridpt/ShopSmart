"""
Tool: Price Scraper — Trích xuất giá từ URL sản phẩm.
Uses BeautifulSoup to extract price from product pages.
"""
import json
import re
import traceback
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


def _extract_price_from_text(text: str) -> float | None:
    """Try to extract a numeric price from text."""
    if not text:
        return None
    # Remove currency symbols and whitespace
    cleaned = text.replace("₫", "").replace("đ", "").replace("VND", "")
    cleaned = cleaned.replace(",", "").replace(".", "").strip()
    # Find the first sequence of digits
    match = re.search(r"\d+", cleaned)
    if match:
        price = int(match.group())
        # Sanity check — prices should be reasonable (> 1000 VND)
        if price > 1000:
            return float(price)
    return None


def _extract_price_jsonld(soup: BeautifulSoup) -> dict | None:
    """Extract price from JSON-LD structured data."""
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Product":
                    offers = item.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    price = offers.get("price") or offers.get("lowPrice")
                    name = item.get("name", "")
                    if price:
                        return {"name": name, "price": float(price)}
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    return None


def _extract_price_meta(soup: BeautifulSoup) -> dict | None:
    """Extract price from Open Graph / meta tags."""
    og_price = soup.find("meta", {"property": "product:price:amount"})
    if og_price and og_price.get("content"):
        try:
            price = float(og_price["content"].replace(",", "").replace(".", ""))
            og_title = soup.find("meta", {"property": "og:title"})
            name = og_title["content"] if og_title else ""
            return {"name": name, "price": price}
        except (ValueError, TypeError):
            pass
    return None


def _extract_price_selectors(soup: BeautifulSoup) -> dict | None:
    """Extract price using common CSS selectors."""
    price_selectors = [
        "[class*='price'] [class*='current']",
        "[class*='product-price']",
        "[class*='price-current']",
        "[class*='sale-price']",
        "[class*='final-price']",
        "[itemprop='price']",
        ".price",
        "#price",
    ]
    for selector in price_selectors:
        elements = soup.select(selector)
        for el in elements:
            price = _extract_price_from_text(el.get_text())
            if price:
                title_tag = soup.find("title")
                name = title_tag.get_text().strip() if title_tag else ""
                return {"name": name, "price": price}
    return None


def scrape_price(url: str) -> str:
    """
    Trích xuất giá sản phẩm từ URL.

    Args:
        url: URL trang sản phẩm cần lấy giá

    Returns:
        JSON string chứa thông tin giá sản phẩm
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Try multiple extraction methods
        result = (
            _extract_price_jsonld(soup)
            or _extract_price_meta(soup)
            or _extract_price_selectors(soup)
        )

        if result:
            return json.dumps({
                "success": True,
                "url": url,
                "product_name": result["name"],
                "price": result["price"],
                "currency": "VND"
            }, ensure_ascii=False)

        # Fallback — get page title
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else "Unknown"

        return json.dumps({
            "success": False,
            "url": url,
            "message": f"Không thể trích xuất giá từ trang này. Trang: {title}",
        }, ensure_ascii=False)

    except requests.RequestException as e:
        return json.dumps({
            "success": False,
            "url": url,
            "message": f"Không thể truy cập URL: {str(e)}"
        }, ensure_ascii=False)
    except Exception as e:
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "url": url,
            "message": f"Lỗi khi scrape giá: {str(e)}"
        }, ensure_ascii=False)


TOOL_DEFINITION = {
    "name": "scrape_price",
    "description": "Trích xuất giá sản phẩm từ một URL cụ thể. Sử dụng khi cần lấy giá chính xác từ một trang web sản phẩm cụ thể.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL đầy đủ của trang sản phẩm (vd: 'https://tiki.vn/iphone-16-p123')"
            }
        },
        "required": ["url"]
    }
}
