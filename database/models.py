"""
ShopSmart Database Models — CRUD operations for all tables.

All product / notification / chat data is scoped by ``user_id``.
Pass ``user_id=None`` only for trusted background jobs (e.g. price monitor)
that need to operate across every user's tracked products.
"""
import json
from datetime import datetime

from database.db import get_db


class User:
    """User account model."""

    @staticmethod
    def create(email, display_name, password_hash):
        with get_db() as conn:
            cursor = conn.execute(
                """INSERT INTO users (email, display_name, password_hash)
                   VALUES (?, ?, ?)""",
                (email, display_name, password_hash),
            )
            return cursor.lastrowid

    @staticmethod
    def get_by_email(email):
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_id(user_id):
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def set_push_subscription(user_id, subscription_json):
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET push_subscription = ? WHERE id = ?",
                (subscription_json, user_id),
            )

    @staticmethod
    def set_notify_email(user_id, enabled):
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET notify_email = ? WHERE id = ?",
                (1 if enabled else 0, user_id),
            )


class Product:
    """Product tracking model (user-scoped)."""

    @staticmethod
    def create(name, url=None, image_url=None, source=None,
               current_price=None, target_price=None, user_id=None):
        with get_db() as conn:
            cursor = conn.execute(
                """INSERT INTO products
                   (user_id, name, url, image_url, source, current_price, target_price)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, name, url, image_url, source, current_price, target_price)
            )
            product_id = cursor.lastrowid
            if current_price is not None:
                conn.execute(
                    "INSERT INTO price_history (product_id, price, source) VALUES (?, ?, ?)",
                    (product_id, current_price, source)
                )
            return product_id

    @staticmethod
    def get_all(user_id=None):
        with get_db() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM products ORDER BY updated_at DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM products WHERE user_id = ? ORDER BY updated_at DESC",
                    (user_id,)
                ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(product_id, user_id=None):
        with get_db() as conn:
            if user_id is None:
                row = conn.execute(
                    "SELECT * FROM products WHERE id = ?", (product_id,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM products WHERE id = ? AND user_id = ?",
                    (product_id, user_id)
                ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_price(product_id, price, source=None):
        with get_db() as conn:
            conn.execute(
                "UPDATE products SET current_price=?, updated_at=? WHERE id=?",
                (price, datetime.now().isoformat(), product_id)
            )
            conn.execute(
                "INSERT INTO price_history (product_id, price, source) VALUES (?, ?, ?)",
                (product_id, price, source)
            )

    @staticmethod
    def update_target_price(product_id, target_price):
        with get_db() as conn:
            conn.execute(
                "UPDATE products SET target_price=?, updated_at=? WHERE id=?",
                (target_price, datetime.now().isoformat(), product_id)
            )

    @staticmethod
    def delete(product_id):
        with get_db() as conn:
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

    @staticmethod
    def search_by_name(name, user_id=None):
        with get_db() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM products WHERE name LIKE ?", (f"%{name}%",)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM products WHERE name LIKE ? AND user_id = ?",
                    (f"%{name}%", user_id)
                ).fetchall()
            return [dict(row) for row in rows]


class PriceHistory:
    """Price history model."""

    @staticmethod
    def get_by_product(product_id, limit=50):
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM price_history
                   WHERE product_id = ?
                   ORDER BY recorded_at ASC LIMIT ?""",
                (product_id, limit)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_stats(product_id):
        with get_db() as conn:
            row = conn.execute(
                """SELECT
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    AVG(price) as avg_price,
                    COUNT(*) as total_records
                   FROM price_history WHERE product_id = ?""",
                (product_id,)
            ).fetchone()
            return dict(row) if row else None


class Notification:
    """Notification model (user-scoped)."""

    @staticmethod
    def create(title, message, product_id=None, ntype="info", user_id=None):
        with get_db() as conn:
            cursor = conn.execute(
                """INSERT INTO notifications (user_id, product_id, title, message, type)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, product_id, title, message, ntype)
            )
            return cursor.lastrowid

    @staticmethod
    def get_all(limit=50, user_id=None):
        with get_db() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM notifications WHERE user_id = ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (user_id, limit)
                ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_unread(user_id=None):
        with get_db() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM notifications WHERE is_read=0 ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM notifications WHERE is_read=0 AND user_id = ?
                       ORDER BY created_at DESC""",
                    (user_id,)
                ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def mark_read(notification_id):
        with get_db() as conn:
            conn.execute(
                "UPDATE notifications SET is_read=1 WHERE id=?",
                (notification_id,)
            )

    @staticmethod
    def mark_all_read(user_id=None):
        with get_db() as conn:
            if user_id is None:
                conn.execute("UPDATE notifications SET is_read=1")
            else:
                conn.execute(
                    "UPDATE notifications SET is_read=1 WHERE user_id = ?",
                    (user_id,)
                )


class ChatHistory:
    """Chat history model (user-scoped)."""

    @staticmethod
    def add(role, content, user_id=None):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )

    @staticmethod
    def get_recent(limit=50, user_id=None):
        with get_db() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM chat_history ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM chat_history WHERE user_id = ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (user_id, limit)
                ).fetchall()
            return list(reversed([dict(row) for row in rows]))

    @staticmethod
    def clear(user_id=None):
        with get_db() as conn:
            if user_id is None:
                conn.execute("DELETE FROM chat_history")
            else:
                conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
