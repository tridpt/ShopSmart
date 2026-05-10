"""
ShopSmart Database Models — CRUD operations for all tables.
"""
from datetime import datetime
from database.db import get_db


class Product:
    """Product tracking model."""

    @staticmethod
    def create(name, url=None, image_url=None, source=None,
               current_price=None, target_price=None):
        with get_db() as conn:
            cursor = conn.execute(
                """INSERT INTO products
                   (name, url, image_url, source, current_price, target_price)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, url, image_url, source, current_price, target_price)
            )
            product_id = cursor.lastrowid
            # Also add first price history entry
            if current_price is not None:
                conn.execute(
                    "INSERT INTO price_history (product_id, price, source) VALUES (?, ?, ?)",
                    (product_id, current_price, source)
                )
            return product_id

    @staticmethod
    def get_all():
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM products ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(product_id):
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
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
    def search_by_name(name):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM products WHERE name LIKE ?", (f"%{name}%",)
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
    """Notification model."""

    @staticmethod
    def create(title, message, product_id=None, ntype="info"):
        with get_db() as conn:
            cursor = conn.execute(
                """INSERT INTO notifications (product_id, title, message, type)
                   VALUES (?, ?, ?, ?)""",
                (product_id, title, message, ntype)
            )
            return cursor.lastrowid

    @staticmethod
    def get_all(limit=50):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_unread():
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM notifications WHERE is_read=0 ORDER BY created_at DESC"
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
    def mark_all_read():
        with get_db() as conn:
            conn.execute("UPDATE notifications SET is_read=1")


class ChatHistory:
    """Chat history model."""

    @staticmethod
    def add(role, content):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO chat_history (role, content) VALUES (?, ?)",
                (role, content)
            )

    @staticmethod
    def get_recent(limit=50):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_history ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return list(reversed([dict(row) for row in rows]))

    @staticmethod
    def clear():
        with get_db() as conn:
            conn.execute("DELETE FROM chat_history")
