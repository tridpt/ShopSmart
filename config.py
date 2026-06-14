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
