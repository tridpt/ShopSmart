"""
Tests for the price monitor's per-product check logic.

We avoid real network calls by monkeypatching `scrape_price` to return canned
JSON, and run against the isolated `db` fixture.
"""
import json

import pytest


def _scrape_returning(price, success=True):
    """Build a fake scrape_price that returns a fixed price."""
    def _fake(url):
        if not success:
            return json.dumps({"success": False, "url": url, "message": "no price"})
        return json.dumps({
            "success": True, "url": url,
            "product_name": "X", "price": price, "currency": "VND",
        })
    return _fake


@pytest.fixture()
def monitor(db, monkeypatch):
    """Reload price_monitor bound to the isolated db/models, return the module."""
    import importlib
    from agent import price_monitor as pm
    importlib.reload(pm)
    # Bind the monitor's Product/Notification/User to the reloaded models.
    monkeypatch.setattr(pm, "Product", db.Product)
    monkeypatch.setattr(pm, "Notification", db.Notification)
    monkeypatch.setattr(pm, "User", db.User)
    return pm


def test_check_product_no_url_returns_none(monitor):
    assert monitor.check_product({"id": 1, "name": "A", "url": None}) is None


def test_check_product_updates_on_price_drop(monitor, db, monkeypatch):
    uid = db.User.create("a@b.com", "A", "hash")
    pid = db.Product.create("Phone", url="https://shop/x", current_price=100_000,
                            target_price=None, user_id=uid)
    monkeypatch.setattr(monitor, "scrape_price", _scrape_returning(90_000))

    product = db.Product.get_by_id(pid)
    result = monitor.check_product(product)

    assert result["changed"] is True
    assert result["new_price"] == 90_000
    assert db.Product.get_by_id(pid)["current_price"] == 90_000
    # A price-drop notification should have been recorded for the owner.
    notifs = db.Notification.get_all(user_id=uid)
    assert any(n["type"] == "alert" for n in notifs)


def test_check_product_target_hit_creates_deal(monitor, db, monkeypatch):
    uid = db.User.create("c@d.com", "C", "hash")
    pid = db.Product.create("TV", url="https://shop/tv", current_price=200_000,
                            target_price=150_000, user_id=uid)
    monkeypatch.setattr(monitor, "scrape_price", _scrape_returning(150_000))

    result = monitor.check_product(db.Product.get_by_id(pid))

    assert result["changed"] is True
    notifs = db.Notification.get_all(user_id=uid)
    assert any(n["type"] == "deal" for n in notifs)


def test_check_product_no_change_is_not_flagged(monitor, db, monkeypatch):
    uid = db.User.create("e@f.com", "E", "hash")
    pid = db.Product.create("Mug", url="https://shop/mug", current_price=50_000,
                            user_id=uid)
    monkeypatch.setattr(monitor, "scrape_price", _scrape_returning(50_000))

    result = monitor.check_product(db.Product.get_by_id(pid))
    assert result["changed"] is False


def test_run_once_scoped_to_user(monitor, db, monkeypatch):
    u1 = db.User.create("u1@x.com", "U1", "h")
    u2 = db.User.create("u2@x.com", "U2", "h")
    db.Product.create("P1", url="https://shop/1", current_price=100_000, user_id=u1)
    db.Product.create("P2", url="https://shop/2", current_price=100_000, user_id=u2)
    monkeypatch.setattr(monitor, "scrape_price", _scrape_returning(80_000))
    # Avoid waiting between items.
    monkeypatch.setattr(monitor._stop_event, "wait", lambda *a, **k: False)

    updated = monitor.run_once(user_id=u1)
    assert updated == 1  # only u1's product
