"""
ShopSmart Database — Connection & Schema Initialization
"""
import sqlite3
import os
from contextlib import contextmanager

import config


def get_connection():
    """Create a new database connection."""
    os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager for database transactions."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database tables."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                push_subscription TEXT,
                notify_email INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                url TEXT,
                image_url TEXT,
                source TEXT,
                current_price REAL,
                target_price REAL,
                currency TEXT DEFAULT 'VND',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                price REAL NOT NULL,
                source TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        # Migrate pre-existing tables BEFORE creating user_id indexes, otherwise
        # the indexes would reference a column that old tables don't have yet.
        _migrate(conn)
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_products_user ON products(user_id);
            CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
            CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id);
        """)
    print("[OK] Database initialized successfully.")


def _migrate(conn):
    """Add user_id columns to pre-existing tables (DBs created before multi-user)."""
    for table in ("products", "notifications", "chat_history"):
        cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if "user_id" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")
            print(f"  [MIGRATE] Added user_id to {table}")

    # users table extra columns (in case an older users table existed)
    ucols = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if ucols:  # table exists
        if "push_subscription" not in ucols:
            conn.execute("ALTER TABLE users ADD COLUMN push_subscription TEXT")
        if "notify_email" not in ucols:
            conn.execute("ALTER TABLE users ADD COLUMN notify_email INTEGER DEFAULT 1")
