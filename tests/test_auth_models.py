"""
Tests for auth helpers (password hashing, JWT) and user-scoped data models.
"""
import importlib

import pytest


@pytest.fixture()
def auth_mod(db, monkeypatch):
    """Reload the auth module bound to the isolated db models."""
    import auth as auth_module
    importlib.reload(auth_module)
    monkeypatch.setattr(auth_module, "User", db.User)
    return auth_module


def test_password_hash_roundtrip(auth_mod):
    h = auth_mod.hash_password("secret123")
    assert h and h != "secret123"
    assert auth_mod.verify_password("secret123", h) is True
    assert auth_mod.verify_password("wrong", h) is False


def test_verify_password_handles_empty_hash(auth_mod):
    assert auth_mod.verify_password("anything", "") is False


def test_jwt_roundtrip(auth_mod):
    token = auth_mod.create_jwt(42)
    payload = auth_mod.verify_jwt(token)
    assert payload["user_id"] == 42


def test_jwt_invalid_token_returns_none(auth_mod):
    assert auth_mod.verify_jwt("not-a-real-token") is None


def test_user_create_and_lookup(db):
    uid = db.User.create("user@x.com", "User", "hash")
    assert db.User.get_by_id(uid)["email"] == "user@x.com"
    assert db.User.get_by_email("user@x.com")["id"] == uid


def test_products_are_user_scoped(db):
    u1 = db.User.create("u1@x.com", "U1", "h")
    u2 = db.User.create("u2@x.com", "U2", "h")
    db.Product.create("P1", current_price=10_000, user_id=u1)
    db.Product.create("P2", current_price=20_000, user_id=u2)

    assert len(db.Product.get_all(user_id=u1)) == 1
    assert db.Product.get_all(user_id=u1)[0]["name"] == "P1"
    assert len(db.Product.get_all(user_id=u2)) == 1


def test_get_by_id_enforces_ownership(db):
    u1 = db.User.create("u1@x.com", "U1", "h")
    u2 = db.User.create("u2@x.com", "U2", "h")
    pid = db.Product.create("Secret", current_price=10_000, user_id=u1)

    assert db.Product.get_by_id(pid, user_id=u1) is not None
    # u2 must not be able to read u1's product.
    assert db.Product.get_by_id(pid, user_id=u2) is None


def test_notifications_user_scoped(db):
    u1 = db.User.create("u1@x.com", "U1", "h")
    u2 = db.User.create("u2@x.com", "U2", "h")
    db.Notification.create("T1", "m", user_id=u1)
    db.Notification.create("T2", "m", user_id=u2)

    assert len(db.Notification.get_all(user_id=u1)) == 1
    assert db.Notification.get_all(user_id=u1)[0]["title"] == "T1"


def test_chat_history_user_scoped(db):
    u1 = db.User.create("u1@x.com", "U1", "h")
    u2 = db.User.create("u2@x.com", "U2", "h")
    db.ChatHistory.add("user", "hello from u1", user_id=u1)
    db.ChatHistory.add("user", "hello from u2", user_id=u2)

    h1 = db.ChatHistory.get_recent(user_id=u1)
    assert len(h1) == 1
    assert h1[0]["content"] == "hello from u1"


def test_set_notify_and_telegram(db):
    uid = db.User.create("u@x.com", "U", "h")
    db.User.set_notify_email(uid, False)
    db.User.set_push_subscription(uid, "12345")
    user = db.User.get_by_id(uid)
    assert user["notify_email"] == 0
    assert user["push_subscription"] == "12345"
