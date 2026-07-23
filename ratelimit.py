"""
Lightweight in-process rate limiting for Flask endpoints.

A token-bucket limiter keyed by identity (authenticated user id when available,
otherwise client IP). No external dependencies. Suitable for a single process;
for multi-worker deployments back this with a shared store (e.g. Redis).
"""
import functools
import threading
import time

from flask import request, jsonify, g

import config


class _TokenBucket:
    __slots__ = ("tokens", "updated")

    def __init__(self, capacity: float):
        self.tokens = capacity
        self.updated = time.monotonic()


class RateLimiter:
    """Token-bucket rate limiter shared across a named group of requests."""

    def __init__(self):
        self._buckets: dict[tuple, _TokenBucket] = {}
        self._lock = threading.Lock()

    def check(self, key: tuple, limit: int, per_seconds: float) -> tuple[bool, float]:
        """Consume one token for ``key``. Returns (allowed, retry_after_seconds)."""
        if limit <= 0 or per_seconds <= 0:
            return True, 0.0
        refill_rate = limit / per_seconds
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _TokenBucket(float(limit))
                self._buckets[key] = bucket
            # Refill based on elapsed time, capped at the bucket capacity.
            elapsed = now - bucket.updated
            bucket.tokens = min(float(limit), bucket.tokens + elapsed * refill_rate)
            bucket.updated = now
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, 0.0
            retry_after = (1.0 - bucket.tokens) / refill_rate
            return False, retry_after

    def reset(self):
        """Clear all buckets (used by tests)."""
        with self._lock:
            self._buckets.clear()


_limiter = RateLimiter()


def _client_identity() -> str:
    """Identity for limiting: authenticated user id, else client IP."""
    user_id = getattr(g, "user_id", None)
    if user_id is not None:
        return f"user:{user_id}"
    # request.remote_addr is set by Werkzeug from the socket; when running behind
    # a trusted proxy configure ProxyFix so this reflects the real client.
    return f"ip:{request.remote_addr or 'unknown'}"


def rate_limit(name: str, limit: int, per_seconds: float):
    """Decorator: allow at most ``limit`` requests per ``per_seconds`` per client.

    Place BELOW ``@login_required`` so authenticated requests are keyed by user
    id; unauthenticated endpoints (login/register) fall back to client IP.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not config.RATE_LIMIT_ENABLED:
                return fn(*args, **kwargs)
            key = (name, _client_identity())
            allowed, retry_after = _limiter.check(key, limit, per_seconds)
            if not allowed:
                retry = max(1, round(retry_after))
                resp = jsonify({
                    "error": "Bạn thao tác quá nhanh. Vui lòng thử lại sau ít giây.",
                    "retry_after": retry,
                })
                resp.status_code = 429
                resp.headers["Retry-After"] = str(retry)
                return resp
            return fn(*args, **kwargs)
        return wrapper
    return decorator
