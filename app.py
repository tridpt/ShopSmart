"""
ShopSmart AI — Flask API Server
"""
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import config
from database.db import init_db
from database.models import Product, PriceHistory, Notification, ChatHistory
from agent.core import ShopSmartAgent

# ── Flask App ───────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder="frontend",
    static_url_path="",
)
CORS(app)

# ── Initialize ──────────────────────────────────────────────
init_db()
agent = None


def get_agent():
    """Lazy-init the agent (so missing API key doesn't crash startup)."""
    global agent
    if agent is None:
        agent = ShopSmartAgent()
    return agent


# ── Frontend Routes ─────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


# ── Chat API ────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    """Send a message to the AI agent."""
    try:
        data = request.get_json()
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # Save user message
        ChatHistory.add("user", message)

        # Process through agent
        ai_agent = get_agent()
        result = ai_agent.process_message(message)

        # Save assistant response
        ChatHistory.add("assistant", result["response"])

        return jsonify({
            "response": result["response"],
            "tool_calls": result["tool_calls"],
            "error": result["error"],
        })

    except ValueError as e:
        # API key not set
        return jsonify({
            "response": str(e),
            "tool_calls": [],
            "error": str(e),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/history", methods=["GET"])
def chat_history():
    """Get recent chat history."""
    try:
        history = ChatHistory.get_recent(50)
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/clear", methods=["POST"])
def clear_chat():
    """Clear chat history and reset agent."""
    try:
        ChatHistory.clear()
        global agent
        if agent:
            agent.reset_chat()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Product Tracking API ────────────────────────────────────
@app.route("/api/tracked", methods=["GET"])
def get_tracked():
    """Get all tracked products."""
    try:
        products = Product.get_all()
        return jsonify({"products": products})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tracked/<int:product_id>", methods=["DELETE"])
def delete_tracked(product_id):
    """Remove a product from tracking."""
    try:
        Product.delete(product_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tracked/<int:product_id>/target", methods=["PUT"])
def update_target(product_id):
    """Update target price for a tracked product."""
    try:
        data = request.get_json()
        target = data.get("target_price")
        Product.update_target_price(product_id, target)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Price History API ────────────────────────────────────────
@app.route("/api/price-history/<int:product_id>", methods=["GET"])
def price_history(product_id):
    """Get price history for a product."""
    try:
        history = PriceHistory.get_by_product(product_id)
        stats = PriceHistory.get_stats(product_id)
        return jsonify({"history": history, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Notifications API ────────────────────────────────────────
@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Get all notifications."""
    try:
        notifications = Notification.get_all()
        unread = len([n for n in notifications if not n["is_read"]])
        return jsonify({"notifications": notifications, "unread_count": unread})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications/read", methods=["POST"])
def mark_notifications_read():
    """Mark all notifications as read."""
    try:
        Notification.mark_all_read()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Health Check ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "api_key_set": bool(config.GEMINI_API_KEY),
        "model": config.GEMINI_MODEL,
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
