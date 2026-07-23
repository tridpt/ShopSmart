import os
from pathlib import Path

# ── Load .env file ──────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# ── Gemini API ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# ── Database ────────────────────────────────────────────────
DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "database", "shopsmart.db"
)

# ── Flask ───────────────────────────────────────────────────
def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))
# Debug defaults to OFF for safety; enable explicitly via FLASK_DEBUG=true.
FLASK_DEBUG = _env_bool("FLASK_DEBUG", False)

# ── Auth / JWT ──────────────────────────────────────────────
def _load_or_create_jwt_secret() -> str:
    """JWT secret from env, or a persisted local one (gitignored) for dev."""
    secret = os.environ.get("JWT_SECRET", "").strip()
    if secret:
        return secret
    secret_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".jwt_secret")
    try:
        if os.path.isfile(secret_file):
            with open(secret_file, "r", encoding="utf-8") as f:
                existing = f.read().strip()
                if existing:
                    return existing
        import secrets as _secrets
        generated = _secrets.token_hex(32)
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(generated)
        print("[WARNING] JWT_SECRET not set — generated a local one in .jwt_secret. "
              "Set JWT_SECRET env var for production!")
        return generated
    except Exception:
        import secrets as _secrets
        return _secrets.token_hex(32)


JWT_SECRET = _load_or_create_jwt_secret()
JWT_EXPIRY_SECONDS = int(os.environ.get("JWT_EXPIRY_SECONDS", str(7 * 24 * 3600)))
# bcrypt work factor; tests can lower via BCRYPT_ROUNDS=4 for speed.
try:
    BCRYPT_ROUNDS = max(4, min(int(os.environ.get("BCRYPT_ROUNDS", "12")), 15))
except ValueError:
    BCRYPT_ROUNDS = 12

# ── Notification Channels (real push) ───────────────────────
# Telegram bot — set both to enable price-drop alerts via Telegram.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

# SMTP email — set all to enable email alerts.
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.environ.get("SMTP_FROM", "").strip() or SMTP_USER

# ── Rate limiting ───────────────────────────────────────────
# Bảo vệ các endpoint tốn tài nguyên (auth brute-force, chi phí Gemini, scrape).
# In-process token bucket; khi chạy nhiều worker nên dùng store dùng chung.
RATE_LIMIT_ENABLED = _env_bool("RATE_LIMIT_ENABLED", True)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


# (limit, per_seconds) cho từng nhóm endpoint.
RATE_LIMIT_AUTH = (_env_int("RATE_LIMIT_AUTH", 10), 60.0)          # login/register
RATE_LIMIT_CHAT = (_env_int("RATE_LIMIT_CHAT", 20), 60.0)          # Gemini chat
RATE_LIMIT_SEARCH = (_env_int("RATE_LIMIT_SEARCH", 30), 60.0)      # search/scrape/compare
RATE_LIMIT_REFRESH = (_env_int("RATE_LIMIT_REFRESH", 6), 60.0)     # làm mới giá thủ công

# ── Agent ───────────────────────────────────────────────────
MAX_AGENT_ITERATIONS = 10

# ── Price Monitor (background auto-update) ──────────────────
# Bật/tắt việc tự động cập nhật giá sản phẩm đang theo dõi.
PRICE_MONITOR_ENABLED = _env_bool("PRICE_MONITOR_ENABLED", True)
# Khoảng thời gian giữa các lần quét (giây). Mặc định 6 giờ.
PRICE_MONITOR_INTERVAL = int(os.environ.get("PRICE_MONITOR_INTERVAL", str(6 * 60 * 60)))
# Đợi bao lâu sau khi khởi động mới quét lần đầu (giây).
PRICE_MONITOR_INITIAL_DELAY = int(os.environ.get("PRICE_MONITOR_INITIAL_DELAY", "60"))
# Khoảng nghỉ giữa các lần scrape từng sản phẩm (giây) để tránh bị chặn.
PRICE_MONITOR_PER_ITEM_DELAY = float(os.environ.get("PRICE_MONITOR_PER_ITEM_DELAY", "3"))
# Có khởi động monitor ngay trong tiến trình web không.
# Khi chạy nhiều worker (gunicorn -w N), ĐẶT false để tránh mỗi worker spawn một
# monitor và quét trùng; thay vào đó chạy monitor riêng bằng `python monitor.py`.
# Mặc định true cho dev / single-process (waitress 1 process vẫn an toàn).
PRICE_MONITOR_IN_PROCESS = _env_bool("PRICE_MONITOR_IN_PROCESS", True)
