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

# Reasonable bounds for a VND product price. Anything outside is treated as noise
# (e.g. installment months, percentages, product codes, ratings).
MIN_VALID_PRICE = 1_000
MAX_VALID_PRICE = 1_000_000_000  # 1 billion VND

# Site-specific price selectors (checked before generic ones).
SITE_SELECTORS = {
    "thegioididong.com": ["p.box-price-present", ".box-price-present", ".price-one"],
    "dienmayxanh.com": ["p.box-price-present", ".box-price-present"],
    "cellphones.com.vn": [".product__price--show", ".box-info__box-price .product__price--show"],
    "fptshop.com.vn": [".st-price-main", ".st-price"],
    "tiki.vn": ["[data-view-id='pdp_main_view_price']", ".product-price__current-price"],
    "hnammobile.com": [".product_price", ".price"],
}


def _parse_vnd(raw: str) -> float | None:
    """
    Parse a VND amount from a string, validating it falls in a sane range.

    Handles formats like '25.990.000đ', '25,990,000 VND', '1.234.567'.
    Both '.' and ',' are treated as thousands separators (VND has no decimals).
    """
    if not raw:
        return None
    # Keep only digits and separators.
    text = re.sub(r"[^\d.,]", "", raw)
    if not text:
        return None

    # Take the first number-like token (longest run of digits/separators).
    match = re.search(r"\d[\d.,]*", text)
    if not match:
        return None

    digits = match.group().replace(".", "").replace(",", "")
    if not digits.isdigit():
        return None

    price = float(digits)
    if MIN_VALID_PRICE <= price <= MAX_VALID_PRICE:
        return price
    return None


def _extract_price_from_text(text: str) -> float | None:
    """Try to extract a valid VND price from arbitrary text."""
    return _parse_vnd(text)


def _extract_price_jsonld(soup: BeautifulSoup) -> dict | None:
    """Extract price from JSON-LD structured data (most reliable)."""
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") == "Product":
                    offers = item.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    raw_price = offers.get("price") or offers.get("lowPrice")
                    name = item.get("name", "")
                    if raw_price is not None:
                        price = _parse_vnd(str(raw_price))
                        if price:
                            return {"name": name, "price": price}
        except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
            continue
    return None


def _extract_price_meta(soup: BeautifulSoup) -> dict | None:
    """Extract price from Open Graph / meta tags."""
    meta_props = ["product:price:amount", "og:price:amount"]
    for prop in meta_props:
        tag = soup.find("meta", {"property": prop})
        if tag and tag.get("content"):
            price = _parse_vnd(tag["content"])
            if price:
                og_title = soup.find("meta", {"property": "og:title"})
                name = og_title["content"] if og_title and og_title.get("content") else ""
                return {"name": name, "price": price}
    return None


def _extract_price_site_specific(soup: BeautifulSoup, url: str) -> dict | None:
    """Extract price using selectors tuned for known Vietnamese e-commerce sites."""
    for domain, selectors in SITE_SELECTORS.items():
        if domain not in url:
            continue
        for selector in selectors:
            for el in soup.select(selector):
                price = _parse_vnd(el.get_text())
                if price:
                    title_tag = soup.find("title")
                    name = title_tag.get_text().strip() if title_tag else ""
                    return {"name": name, "price": price}
    return None


def _extract_price_selectors(soup: BeautifulSoup) -> dict | None:
    """Extract price using common generic CSS selectors."""
    price_selectors = [
        "[itemprop='price']",
        "[class*='price'] [class*='current']",
        "[class*='product-price']",
        "[class*='price-current']",
        "[class*='sale-price']",
        "[class*='final-price']",
        ".price",
        "#price",
    ]
    for selector in price_selectors:
        for el in soup.select(selector):
            # itemprop=price often stores the value in a 'content' attribute.
            price = _parse_vnd(el.get("content", "")) or _parse_vnd(el.get_text())
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
    # Basic URL validation.
    if not url or not re.match(r"^https?://", url.strip(), re.IGNORECASE):
        return json.dumps({
            "success": False,
            "url": url,
            "message": "URL không hợp lệ. URL phải bắt đầu bằng http:// hoặc https://"
        }, ensure_ascii=False)

    url = url.strip()
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Try multiple extraction methods, most reliable first.
        result = (
            _extract_price_jsonld(soup)
            or _extract_price_meta(soup)
            or _extract_price_site_specific(soup, url)
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

        # Fallback — get page title.
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else "Unknown"

        return json.dumps({
            "success": False,
            "url": url,
            "message": f"Không thể trích xuất giá từ trang này (có thể trang dùng JavaScript để hiển thị giá). Trang: {title}",
        }, ensure_ascii=False)

    except requests.Timeout:
        return json.dumps({
            "success": False,
            "url": url,
            "message": "Hết thời gian chờ khi truy cập URL (timeout 15s)."
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
