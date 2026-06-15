"""
Tests for price extraction — the most fragile part of the app.
We test the pure parsing helpers (no network) plus JSON-LD / meta extraction.
"""
from bs4 import BeautifulSoup

from agent.tools import price_scraper as ps


class TestExtractPriceFromText:
    def test_vnd_with_dots(self):
        assert ps._extract_price_from_text("25.990.000đ") == 25990000.0

    def test_vnd_with_commas(self):
        assert ps._extract_price_from_text("25,990,000 VND") == 25990000.0

    def test_rejects_installment_zero_percent(self):
        assert ps._extract_price_from_text("Trả góp 0%") is None

    def test_rejects_month_count(self):
        assert ps._extract_price_from_text("12 tháng") is None

    def test_rejects_discount_percent(self):
        assert ps._extract_price_from_text("Giảm 50%") is None

    def test_rejects_too_small(self):
        assert ps._extract_price_from_text("999") is None

    def test_rejects_too_large(self):
        # 2 tỷ -> above the sane upper bound
        assert ps._extract_price_from_text("2.000.000.000") is None

    def test_rejects_rating(self):
        assert ps._extract_price_from_text("rating 4.5") is None

    def test_empty(self):
        assert ps._extract_price_from_text("") is None
        assert ps._extract_price_from_text(None) is None


class TestExtractJsonLd:
    def test_product_offer_price(self):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type":"Product","name":"iPhone 16","offers":{"price":"22990000"}}
        </script>
        </head><body></body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        result = ps._extract_price_jsonld(soup)
        assert result is not None
        assert result["price"] == 22990000.0
        assert result["name"] == "iPhone 16"

    def test_offers_as_list(self):
        html = """
        <script type="application/ld+json">
        {"@type":"Product","name":"X","offers":[{"price":"1500000"}]}
        </script>
        """
        soup = BeautifulSoup(html, "lxml")
        result = ps._extract_price_jsonld(soup)
        assert result["price"] == 1500000.0

    def test_no_jsonld(self):
        soup = BeautifulSoup("<html><body>nothing</body></html>", "lxml")
        assert ps._extract_price_jsonld(soup) is None

    def test_malformed_jsonld_is_ignored(self):
        html = '<script type="application/ld+json">{not valid json}</script>'
        soup = BeautifulSoup(html, "lxml")
        assert ps._extract_price_jsonld(soup) is None
