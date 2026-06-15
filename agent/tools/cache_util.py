"""
Lightweight in-memory TTL cache + a simple rate limiter.

Both are thread-safe and dependency-free. Used by the web search tool to avoid
hammering DuckDuckGo (which returns HTTP 429 when called too frequently) and to
serve repeated queries instantly.
"""
import threading
import time


class TTLCache:
    """Thread-safe in-memory cache where each entry expires after `ttl` seconds."""

    def __init__(self, ttl: float = 300.0, max_entries: int = 256):
        self._ttl = ttl
        self._max = max_entries
        self._store = {}  # key -> (expires_at, value)
        self._lock = threading.Lock()

    def get(self, key, allow_stale: bool = False):
        """
        Return the cached value, or None.

        If `allow_stale` is True, an expired entry is still returned (used as a
        graceful fallback when we're rate-limited and can't fetch fresh data).
        """
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if now >= expires_at:
                if allow_stale:
                    return value
                self._store.pop(key, None)
                return None
            return value

    def set(self, key, value):
        now = time.time()
        with self._lock:
            # Opportunistic cleanup of expired / overflowing entries.
            if len(self._store) >= self._max:
                expired = [k for k, (exp, _) in self._store.items() if now >= exp]
                for k in expired:
                    self._store.pop(k, None)
                # Still full? Drop the soonest-to-expire entry.
                if len(self._store) >= self._max:
                    oldest = min(self._store, key=lambda k: self._store[k][0])
                    self._store.pop(oldest, None)
            self._store[key] = (now + self._ttl, value)

    def clear(self):
        with self._lock:
            self._store.clear()


class RateLimiter:
    """
    Sliding-window limiter: allow at most `max_calls` within `period` seconds.

    `acquire()` returns True if a slot was consumed, False if the caller should
    back off. `time_until_next()` reports how long until a slot frees up.
    """

    def __init__(self, max_calls: int = 8, period: float = 60.0):
        self._max = max_calls
        self._period = period
        self._calls = []  # timestamps
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        now = time.time()
        with self._lock:
            # Drop timestamps outside the window.
            cutoff = now - self._period
            self._calls = [t for t in self._calls if t > cutoff]
            if len(self._calls) < self._max:
                self._calls.append(now)
                return True
            return False

    def time_until_next(self) -> float:
        """Seconds until the oldest in-window call expires (a slot frees up)."""
        now = time.time()
        with self._lock:
            cutoff = now - self._period
            self._calls = [t for t in self._calls if t > cutoff]
            if len(self._calls) < self._max:
                return 0.0
            return max(0.0, self._calls[0] + self._period - now)
