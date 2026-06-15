"""
Standalone price-monitor process.

Run this as a SINGLE separate process when the web app is scaled across multiple
workers (so prices aren't re-scraped once per worker). In that setup, set
PRICE_MONITOR_IN_PROCESS=false for the web server and run:

    python monitor.py

It runs the same monitoring loop used in-process, but on its own. The loop
itself is a daemon thread, so we keep the main thread alive until interrupted.
"""
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from database.db import init_db
from agent import price_monitor


def main():
    print("=" * 50)
    print("ShopSmart AI — Standalone price monitor")
    print("=" * 50)
    init_db()

    if not config.PRICE_MONITOR_ENABLED:
        print("[INFO] PRICE_MONITOR_ENABLED=false — nothing to do. Exiting.")
        return

    price_monitor.start_monitor()
    print(f"[OK] Monitor running (interval={config.PRICE_MONITOR_INTERVAL}s). Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping monitor...")
        price_monitor.stop_monitor()


if __name__ == "__main__":
    main()
