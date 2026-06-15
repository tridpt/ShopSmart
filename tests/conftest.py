"""
Pytest fixtures for ShopSmart.

Every test runs against an isolated temporary SQLite database so we never touch
the real shopsmart.db. We point config.DATABASE_PATH at a tmp file and (re)init
the schema before each test, then reset module-level state as needed.
"""
import os
import sys
import importlib

import pytest

# Ensure project root on path.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Keep bcrypt fast in tests.
os.environ.setdefault("BCRYPT_ROUNDS", "4")
# Don't spawn the background price monitor during tests.
os.environ.setdefault("PRICE_MONITOR_ENABLED", "false")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Provide a fresh, isolated database for a test."""
    import config
    db_file = tmp_path / "test_shopsmart.db"
    monkeypatch.setattr(config, "DATABASE_PATH", str(db_file))

    # Re-import db module bound to the patched config path and init schema.
    from database import db as db_module
    importlib.reload(db_module)
    db_module.init_db()

    # Reload models so they use the freshly reloaded db module.
    from database import models as models_module
    importlib.reload(models_module)

    return models_module
