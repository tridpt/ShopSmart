"""
Tests for web_search URL filtering — keep real product pages, drop blog/news/promo.
"""
from agent.tools import web_search as ws


def test_rejects_blog_and_news_urls():
    assert ws._is_product_url("https://cellphones.com.vn/sforum/danh-gia-iphone-15") is False
    assert ws._is_product_url("https://tiki.vn/blog/tinh-nang-iphone-15") is False
    assert ws._is_product_url("https://tiki.vn/khuyen-mai/apple-iphone-15") is False
    assert ws._is_product_url("https://www.thegioididong.com/tin-tuc/abc") is False


def test_accepts_product_urls():
    assert ws._is_product_url("https://tiki.vn/dien-thoai-iphone-15-p123456.html") is True
    assert ws._is_product_url("https://www.thegioididong.com/dtdd/iphone-15-pro-max") is True
    assert ws._is_product_url("https://cellphones.com.vn/iphone-15.html") is True


def test_rejects_empty_and_bare_domain():
    assert ws._is_product_url("") is False
    assert ws._is_product_url("https://www.apple.com/iphone/") is False
