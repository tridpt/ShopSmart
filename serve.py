"""
Production server launcher using waitress (cross-platform: Windows + Linux).

Usage:
    python serve.py

Reads host/port/threads from environment (see .env.example). Unlike `app.py`
(the dev server), this runs a real WSGI server. The background price monitor
starts here once — controlled by PRICE_MONITOR_IN_PROCESS / PRICE_MONITOR_ENABLED.

If you scale out to multiple server processes (e.g. gunicorn -w 4), set
PRICE_MONITOR_IN_PROCESS=false and run `python monitor.py` as a single separate
process so prices aren't re-scraped once per worker.
"""
import os
import sys

# Match app.py's console encoding fix for Vietnamese output on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from waitress import serve

import config
from app import app


def main():
    host = config.FLASK_HOST if config.FLASK_HOST != "127.0.0.1" else os.environ.get("SERVE_HOST", "0.0.0.0")
    port = config.FLASK_PORT
    threads = int(os.environ.get("SERVE_THREADS", "8"))

    print("=" * 50)
    print("ShopSmart AI — Production server (waitress)")
    print("=" * 50)
    if not config.GEMINI_API_KEY:
        print("[WARNING] GEMINI_API_KEY not set — chat features will be disabled.")
    else:
        print("[OK] API Key detected.")
    print(f"Serving on http://{host}:{port}  (threads={threads})")
    print(f"Price monitor in-process: {config.PRICE_MONITOR_IN_PROCESS and config.PRICE_MONITOR_ENABLED}")
    print("=" * 50)

    serve(app, host=host, port=port, threads=threads)


if __name__ == "__main__":
    main()
