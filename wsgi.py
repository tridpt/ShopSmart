"""
WSGI entrypoint for production servers (waitress / gunicorn / uwsgi).

Examples:
    # Windows or cross-platform (waitress):
    waitress-serve --host=0.0.0.0 --port=5000 wsgi:app

    # Linux (gunicorn, 4 workers):
    #   Set PRICE_MONITOR_IN_PROCESS=false and run a separate `python monitor.py`
    #   so the price monitor doesn't run once per worker.
    gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
"""
from app import app  # noqa: F401  (re-exported as the WSGI callable)
