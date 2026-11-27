"""Report whether the local SQLite preview database predates Alembic management."""

import os
import sqlite3
from pathlib import Path

from sqlalchemy.engine import make_url


database_url = make_url(os.environ["COMMANDOS_DATABASE_URL"])
if database_url.drivername != "sqlite" or not database_url.database:
    print("managed")
    raise SystemExit(0)

database_path = Path(database_url.database)
if not database_path.exists():
    print("new")
    raise SystemExit(0)

with sqlite3.connect(database_path) as connection:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    migration_version = None
    if "alembic_version" in tables:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        migration_version = row[0] if row else None

if "creator_watchlist_items" in tables and not migration_version:
    print("legacy")
else:
    print("managed")
