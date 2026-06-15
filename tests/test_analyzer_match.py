"""
Tests for the smarter product-name matching used by analyze_price:
accent-insensitive normalization, token-overlap scoring, and ranking.
"""
from agent.tools import price_analyzer as pa


def test_normalize_strips_accents():
    assert pa._normalize("Điện Thoại iPhone") == "dien thoai iphone"
    assert pa._normalize("Tai nghe  Bluetooth!!") == "tai nghe bluetooth"


def test_match_score_exact_is_one():
    assert pa._match_score("iPhone 16", "iPhone 16") == 1.0


def test_match_score_prefers_more_specific():
    q = "iPhone 16 Pro"
    s_pro = pa._match_score(q, "iPhone 16 Pro Max")
    s_plain = pa._match_score(q, "iPhone 16")
    assert s_pro > s_plain


def test_match_score_unrelated_is_low():
    assert pa._match_score("iPhone 16", "Máy giặt LG") < 0.3


def test_rank_matches_orders_by_score():
    products = [
        {"id": 1, "name": "iPhone 16"},
        {"id": 2, "name": "iPhone 16 Pro Max 256GB"},
        {"id": 3, "name": "Ốp lưng iPhone"},
    ]
    ranked = pa._rank_matches("iPhone 16 Pro Max", products)
    assert ranked[0][0]["id"] == 2  # best match first


def test_analyze_price_ambiguous(db, monkeypatch):
    """Two near-equal matches → ambiguous response asking to disambiguate."""
    import json
    import importlib
    from agent.tools import price_analyzer as analyzer
    importlib.reload(analyzer)
    monkeypatch.setattr(analyzer, "Product", db.Product)
    monkeypatch.setattr(analyzer, "PriceHistory", db.PriceHistory)
    uid = db.User.create("u@x.com", "U", "hash")
    monkeypatch.setattr(analyzer, "get_current_user_id", lambda: uid)

    db.Product.create("Laptop Dell XPS 13", current_price=30_000_000, user_id=uid)
    db.Product.create("Laptop Dell XPS 15", current_price=40_000_000, user_id=uid)

    out = json.loads(analyzer.analyze_price("Laptop Dell XPS"))
    assert out["success"] is False
    assert out.get("ambiguous") is True
    assert len(out["matches"]) == 2
