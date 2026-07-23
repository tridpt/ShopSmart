"""
ShopSmart AI — Flask API Server
"""
import os
import re
import sys

# Fix Windows console encoding for Vietnamese text
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_from_directory, g, Response
from flask_cors import CORS

import config
from database.db import init_db
from database.models import Product, PriceHistory, Notification, ChatHistory, User
from agent.core import ShopSmartAgent
from agent import price_monitor, notify_channels
from auth import (
    login_required, current_user_id, create_jwt,
    hash_password, verify_password,
)
from ratelimit import rate_limit

# ── Flask App ───────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder="frontend",
    static_url_path="",
)
# The frontend is served same-origin by Flask, so cross-origin access is off by
# default. Set CORS_ORIGINS only when hosting the frontend on a separate domain.
if config.CORS_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}},
         supports_credentials=True)

# ── Initialize ──────────────────────────────────────────────
init_db()
# Only start the background monitor inside the web process when configured to.
# For multi-worker deployments (gunicorn -w N), set PRICE_MONITOR_IN_PROCESS=false
# and run a single dedicated monitor process via `python monitor.py` instead, so
# tracked products aren't re-scraped N times in parallel.
if config.PRICE_MONITOR_IN_PROCESS:
    price_monitor.start_monitor()

# Per-user agent sessions (each user gets an isolated chat context).
_agents = {}


def get_agent(user_id):
    """Lazy-init a per-user agent (so missing API key doesn't crash startup)."""
    agent = _agents.get(user_id)
    if agent is None:
        agent = ShopSmartAgent()
        _agents[user_id] = agent
    return agent


def _safe_user(user: dict) -> dict:
    """Strip sensitive fields before returning a user to the client."""
    if not user:
        return {}
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "notify_email": bool(user.get("notify_email", 1)),
        "has_telegram": bool((user.get("push_subscription") or "").strip()),
    }


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── Frontend Routes ─────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


# ── Auth API ────────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
@rate_limit("auth", *config.RATE_LIMIT_AUTH)
def register():
    """Register a new account."""
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").lower().strip()
        password = data.get("password") or ""
        display_name = (data.get("display_name") or "").strip()

        if not _EMAIL_RE.match(email):
            return jsonify({"error": "Email không hợp lệ"}), 400
        if len(password) < 6:
            return jsonify({"error": "Mật khẩu tối thiểu 6 ký tự"}), 400
        if not display_name:
            return jsonify({"error": "Vui lòng nhập tên hiển thị"}), 400
        if User.get_by_email(email):
            return jsonify({"error": "Email này đã được đăng ký"}), 409

        user_id = User.create(email, display_name, hash_password(password))
        token = create_jwt(user_id)
        return jsonify({"token": token, "user": _safe_user(User.get_by_id(user_id))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/login", methods=["POST"])
@rate_limit("auth", *config.RATE_LIMIT_AUTH)
def login():
    """Login with email and password."""
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").lower().strip()
        password = data.get("password") or ""

        user = User.get_by_email(email)
        if not user or not verify_password(password, user["password_hash"]):
            return jsonify({"error": "Email hoặc mật khẩu không đúng"}), 401

        token = create_jwt(user["id"])
        return jsonify({"token": token, "user": _safe_user(user)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/me", methods=["GET"])
@login_required
def get_me():
    """Return the current authenticated user."""
    return jsonify({"user": _safe_user(User.get_by_id(g.user_id))})


@app.route("/api/auth/settings", methods=["PUT"])
@login_required
def update_settings():
    """Update notification settings: email toggle and Telegram chat id."""
    try:
        data = request.get_json(silent=True) or {}
        if "notify_email" in data:
            User.set_notify_email(g.user_id, bool(data["notify_email"]))
        if "telegram_chat_id" in data:
            chat_id = (data.get("telegram_chat_id") or "").strip()
            User.set_push_subscription(g.user_id, chat_id)
        return jsonify({"user": _safe_user(User.get_by_id(g.user_id))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Chat API ────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
@login_required
@rate_limit("chat", *config.RATE_LIMIT_CHAT)
def chat():
    """Send a message to the AI agent."""
    try:
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()

        if not message:
            return jsonify({"error": "Message is required"}), 400

        ChatHistory.add("user", message, user_id=g.user_id)

        ai_agent = get_agent(g.user_id)
        result = ai_agent.process_message(message, user_id=g.user_id)

        ChatHistory.add("assistant", result["response"], user_id=g.user_id)

        return jsonify({
            "response": result["response"],
            "tool_calls": result["tool_calls"],
            "error": result["error"],
        })

    except ValueError as e:
        return jsonify({
            "response": str(e),
            "tool_calls": [],
            "error": str(e),
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "response": f"Loi: {str(e)}",
            "tool_calls": [],
            "error": str(e),
        }), 200


@app.route("/api/chat/history", methods=["GET"])
@login_required
def chat_history():
    """Get recent chat history."""
    try:
        history = ChatHistory.get_recent(50, user_id=g.user_id)
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/clear", methods=["POST"])
@login_required
def clear_chat():
    """Clear chat history and reset agent."""
    try:
        ChatHistory.clear(user_id=g.user_id)
        agent = _agents.get(g.user_id)
        if agent:
            agent.reset_chat()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Product Tracking API ────────────────────────────────────
@app.route("/api/tracked", methods=["GET"])
@login_required
def get_tracked():
    """Get all tracked products for the current user."""
    try:
        products = Product.get_all(user_id=g.user_id)
        return jsonify({"products": products})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tracked/<int:product_id>", methods=["DELETE"])
@login_required
def delete_tracked(product_id):
    """Remove a product from tracking (only if it belongs to the user)."""
    try:
        if not Product.get_by_id(product_id, user_id=g.user_id):
            return jsonify({"error": "Product not found"}), 404
        Product.delete(product_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tracked/<int:product_id>/target", methods=["PUT"])
@login_required
def update_target(product_id):
    """Update target price for a tracked product owned by the user."""
    try:
        if not Product.get_by_id(product_id, user_id=g.user_id):
            return jsonify({"error": "Product not found"}), 404

        data = request.get_json(silent=True) or {}
        target = data.get("target_price")

        if target is not None:
            try:
                target = float(target)
            except (TypeError, ValueError):
                return jsonify({"error": "target_price must be a number"}), 400
            if target <= 0:
                return jsonify({"error": "target_price must be greater than 0"}), 400

        Product.update_target_price(product_id, target)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/track", methods=["POST"])
@login_required
def track_product():
    """Track a product directly from the search UI (no AI/chat needed)."""
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or data.get("product_name") or "").strip()
        if not name:
            return jsonify({"error": "Tên sản phẩm là bắt buộc"}), 400

        url = (data.get("url") or "").strip() or None
        source = (data.get("source") or "").strip() or None

        def _num(key):
            val = data.get(key)
            if val is None or val == "":
                return None
            try:
                f = float(val)
            except (TypeError, ValueError):
                return "invalid"
            return f if f > 0 else "invalid"

        current_price = _num("current_price")
        target_price = _num("target_price")
        if current_price == "invalid":
            return jsonify({"error": "current_price phải là số dương"}), 400
        if target_price == "invalid":
            return jsonify({"error": "target_price phải là số dương"}), 400

        product_id = Product.create(
            name=name, url=url, source=source,
            current_price=current_price, target_price=target_price,
            user_id=g.user_id,
        )
        Notification.create(
            title="📌 Đã thêm vào theo dõi",
            message=f"'{name}' đã được thêm vào danh sách theo dõi giá.",
            product_id=product_id, ntype="tracking", user_id=g.user_id,
        )
        return jsonify({"success": True, "product_id": product_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tracked/export", methods=["GET"])
@login_required
def export_tracked():
    """Export the user's tracked products as a CSV download."""
    try:
        import csv
        import io

        products = Product.get_all(user_id=g.user_id)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "name", "source", "url",
            "current_price", "target_price", "currency",
            "created_at", "updated_at",
        ])
        for p in products:
            writer.writerow([
                p.get("id"), p.get("name"), p.get("source"), p.get("url"),
                p.get("current_price"), p.get("target_price"),
                p.get("currency"), p.get("created_at"), p.get("updated_at"),
            ])

        # Prepend a UTF-8 BOM so Excel renders Vietnamese characters correctly.
        csv_data = "\ufeff" + buf.getvalue()
        return Response(
            csv_data,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=shopsmart_tracked.csv",
            },
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Price History API ────────────────────────────────────────
@app.route("/api/price-history/<int:product_id>", methods=["GET"])
@login_required
def price_history(product_id):
    """Get price history for a product owned by the user."""
    try:
        if not Product.get_by_id(product_id, user_id=g.user_id):
            return jsonify({"error": "Product not found"}), 404
        history = PriceHistory.get_by_product(product_id)
        stats = PriceHistory.get_stats(product_id)
        return jsonify({"history": history, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Notifications API ────────────────────────────────────────
@app.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    """Get notifications for the current user."""
    try:
        notifications = Notification.get_all(user_id=g.user_id)
        unread = len([n for n in notifications if not n["is_read"]])
        return jsonify({"notifications": notifications, "unread_count": unread})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications/read", methods=["POST"])
@login_required
def mark_notifications_read():
    """Mark all of the user's notifications as read."""
    try:
        Notification.mark_all_read(user_id=g.user_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Price Monitor API ────────────────────────────────────────
@app.route("/api/refresh-prices", methods=["POST"])
@login_required
@rate_limit("refresh", *config.RATE_LIMIT_REFRESH)
def refresh_prices():
    """Trigger an immediate price re-check for the user's tracked products."""
    try:
        updated = price_monitor.run_once(user_id=g.user_id)
        return jsonify({"success": True, "updated": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Direct Search API (no AI needed) ────────────────────────
@app.route("/api/search", methods=["GET"])
@login_required
@rate_limit("search", *config.RATE_LIMIT_SEARCH)
def direct_search():
    """Search products directly without Gemini AI."""
    try:
        from agent.tools.web_search import search_product
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        result_json = search_product(query, max_results=12)
        import json
        result = json.loads(result_json)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Price Scraper API (no AI needed) ─────────────────────────
@app.route("/api/scrape-price", methods=["POST"])
@login_required
@rate_limit("search", *config.RATE_LIMIT_SEARCH)
def scrape_price_api():
    """Scrape real price from a product URL."""
    try:
        from agent.tools.price_scraper import scrape_price
        import json as _json

        data = request.get_json(silent=True) or {}
        url = data.get("url", "").strip() if data else ""
        if not url:
            return jsonify({"error": "URL is required"}), 400
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return jsonify({"error": "URL must start with http:// or https://"}), 400

        result_json = scrape_price(url)
        result = _json.loads(result_json)

        if result.get("price"):
            price = result["price"]
            result["price_formatted"] = f"{price:,.0f}đ".replace(",", ".")

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Price Comparison API (gom giá đa sàn) ───────────────────
@app.route("/api/compare", methods=["GET"])
@login_required
@rate_limit("search", *config.RATE_LIMIT_SEARCH)
def compare_prices():
    """
    Search a product, scrape prices from each source, group them into one
    comparison table and flag the cheapest. Limited scraping to stay responsive.
    """
    try:
        from agent.tools.web_search import search_product
        from agent.tools.price_scraper import scrape_price
        import json as _json

        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        # How many result URLs to actually scrape prices for (cost control).
        try:
            limit = max(1, min(int(request.args.get("limit", "6")), 10))
        except (TypeError, ValueError):
            limit = 6

        search = _json.loads(search_product(query, max_results=12))
        results = search.get("results", []) if search.get("success") else []

        # Keep the first result per source so we compare across distinct sellers.
        by_source = {}
        for r in results:
            src = r.get("source") or "Web"
            if src not in by_source and r.get("url"):
                by_source[src] = r
            if len(by_source) >= limit:
                break

        offers = []
        for src, r in by_source.items():
            offer = {
                "source": src,
                "product_name": r.get("product_name"),
                "url": r.get("url"),
                "price": None,
                "price_formatted": None,
            }
            try:
                scraped = _json.loads(scrape_price(r["url"]))
                if scraped.get("price"):
                    offer["price"] = scraped["price"]
                    offer["price_formatted"] = f"{scraped['price']:,.0f}đ".replace(",", ".")
            except Exception:
                pass
            offers.append(offer)

        priced = [o for o in offers if o["price"] is not None]
        priced.sort(key=lambda o: o["price"])
        cheapest_source = priced[0]["source"] if priced else None
        for o in offers:
            o["is_cheapest"] = (o["source"] == cheapest_source and o["price"] is not None)

        # Show priced offers first (sorted), then the ones we couldn't price.
        ordered = priced + [o for o in offers if o["price"] is None]

        return jsonify({
            "success": True,
            "query": query,
            "total_offers": len(ordered),
            "priced_count": len(priced),
            "cheapest_source": cheapest_source,
            "offers": ordered,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Health Check ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "api_key_set": bool(config.GEMINI_API_KEY),
        "model": config.GEMINI_MODEL,
        "channels": {
            "telegram": notify_channels.telegram_configured(),
            "email": notify_channels.email_configured(),
        },
    })


# ── Main ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("ShopSmart AI Agent")
    print("=" * 50)

    if not config.GEMINI_API_KEY:
        print("[WARNING] GEMINI_API_KEY not set!")
        print("   Run: set GEMINI_API_KEY=your_key_here")
        print("   Or:  $env:GEMINI_API_KEY='your_key_here'")
    else:
        print("[OK] API Key detected.")

    print(f"Server: http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    print("=" * 50)

    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
