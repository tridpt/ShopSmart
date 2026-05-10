import os

# ── Gemini API ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

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
