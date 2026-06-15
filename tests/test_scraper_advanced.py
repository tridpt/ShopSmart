"""
Tests for the advanced price-scraping strategies: embedded-JSON mining
(JS-render rescue), JSON-LD, meta tags, and the VND parser bounds.
"""
from bs4 import BeautifulSoup

from agent.tools import price_scraper as ps


def _soup(html):
    return BeautifulSoup(html, "lxml")


# ── _parse_vnd ──────────────────────────────────────────────
def test_parse_vnd_formats():
    assert ps._parse_vnd("25.990.000đ") == 25_990_000
    assert ps._parse_vnd("25,990,000 VND") == 25_990_000
    assert ps._parse_vnd("1.234.567") == 1_234_567
    assert ps._parse_vnd(199000) == 199_000  # raw number


def test_parse_vnd_rejects_noise():
    assert ps._parse_vnd("Trả góp 0%") is None
    assert ps._parse_vnd("12 tháng") is None
    assert ps._parse_vnd("999") is None              # below MIN
    assert ps._parse_vnd("2.000.000.000") is None    # above MAX
    assert ps._parse_vnd("") is None
    assert ps._parse_vnd(None) is None


# ── JSON-LD ─────────────────────────────────────────────────
def test_jsonld_extraction():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type":"Product","name":"iPhone 16","offers":{"price":"22990000"}}
    </script>
    </head><body></body></html>
    """
    result = ps._extract_price_jsonld(_soup(html))
    assert result and result["price"] == 22_990_000
    assert result["name"] == "iPhone 16"


# ── Meta tags ───────────────────────────────────────────────
def test_meta_extraction():
    html = """
    <html><head>
    <meta property="product:price:amount" content="5990000">
    <meta property="og:title" content="Tai nghe XYZ">
    </head><body></body></html>
    """
    result = ps._extract_price_meta(_soup(html))
    assert result and result["price"] == 5_990_000
    assert result["name"] == "Tai nghe XYZ"


# ── Embedded JSON (JS-render rescue) ────────────────────────
def test_embedded_json_script_block():
    html = """
    <html><head><title>Sản phẩm A</title></head><body>
    <script type="application/json">
    {"product":{"id":1,"salePrice":18990000,"listPrice":21990000}}
    </script>
    </body></html>
    """
    result = ps._extract_price_embedded_json(_soup(html))
    # salePrice is preferred over listPrice.
    assert result and result["price"] == 18_990_000


def test_embedded_json_inline_assignment():
    html = """
    <html><head><title>Sản phẩm B</title></head><body>
    <script>window.__DATA__ = {"data":{"current_price":3490000}};</script>
    </body></html>
    """
    result = ps._extract_price_embedded_json(_soup(html))
    assert result and result["price"] == 3_490_000


def test_walk_json_prefers_sale_over_list():
    obj = {"a": {"list_price": 100000, "salePrice": 80000}}
    assert ps._walk_json_for_price(obj) == 80_000


def test_scrape_price_rejects_bad_url():
    import json
    out = json.loads(ps.scrape_price("not-a-url"))
    assert out["success"] is False
