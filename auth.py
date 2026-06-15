"""
ShopSmart — Authentication (JWT + bcrypt) for Flask.

Provides user registration/login, JWT issuing/verification, and a
`@login_required` decorator that injects the current user id into the request.
"""
import functools
import time

import bcrypt
import jwt as pyjwt
from flask import request, jsonify, g

import config
from database.models import User


def hash_password(password: str) -> str:
    rounds = config.BCRYPT_ROUNDS
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_jwt(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + config.JWT_EXPIRY_SECONDS,
    }
    return pyjwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def verify_jwt(token: str):
    try:
        return pyjwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        return None
    except pyjwt.InvalidTokenError:
        return None


def _token_from_request():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def current_user_id():
    """Return the authenticated user's id, or None."""
    token = _token_from_request()
    if not token:
        return None
    payload = verify_jwt(token)
    if not payload:
        return None
    return payload.get("user_id")


def login_required(fn):
    """Decorator: reject unauthenticated requests, set g.user_id otherwise."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        uid = current_user_id()
        if uid is None:
            return jsonify({"error": "Chưa đăng nhập hoặc phiên đã hết hạn"}), 401
        # Make sure the user still exists.
        if not User.get_by_id(uid):
            return jsonify({"error": "Tài khoản không tồn tại"}), 401
        g.user_id = uid
        return fn(*args, **kwargs)
    return wrapper
