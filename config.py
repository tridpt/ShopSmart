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
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True

# ── Agent ───────────────────────────────────────────────────
MAX_AGENT_ITERATIONS = 10
