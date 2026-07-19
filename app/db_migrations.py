"""Database migration system for Meta CCCO Engine.

Usage
-----
Migrations are registered with the ``@register`` decorator and run
automatically on application startup (after ``init_db()`` creates the base
tables). Each migration receives a writable SQLite connection and must be
idempotent (use ``CREATE TABLE IF NOT EXISTS`` / ``ALTER TABLE ... ADD COLUMN``
/ ``INSERT OR IGNORE`` patterns).

Adding a new migration::

    from app.db_migrations import register

    @register(version=2, description="Add widget_type column to ccco_campaigns")
    def add_widget_type(conn):
        conn.execute("ALTER TABLE ccco_campaigns ADD COLUMN widget_type TEXT DEFAULT 'standard'")
        conn.commit()

Version numbers must be monotonically increasing integers. Once a migration has
been applied its version is recorded in the ``schema_migrations`` table and it
will never run again for that database.

Design decisions
----------------
- No external dependency (not Alembic). The schema is simple enough that a
  hand-rolled versioned runner is more auditable and avoids pulling in
  SQLAlchemy just for migrations.
- Migrations run inside the server process at startup (synchronous, before the
  first request). This is acceptable for a single-process FastAPI + SQLite
  deployment. A future distributed deployment should extract migrations into a
  CLI command or a separate init container.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.utils.logging import structlog

logger = structlog.get_logger()

# In-memory registry: (version, description, callable)
_MIGRATIONS: list[tuple[int, str, Callable[[sqlite3.Connection], None]]] = []


def register(
    version: int, description: str
) -> Callable[
    [Callable[[sqlite3.Connection], None]], Callable[[sqlite3.Connection], None]
]:
    """Decorator that registers a migration function.

    Args:
        version: Monotonically increasing integer version number.
        description: Human-readable description of what the migration does.

    Example::

        @register(version=2, description="Add widget_type column")
        def migrate(conn):
            conn.execute("ALTER TABLE ...")
            conn.commit()
    """

    def decorator(
        fn: Callable[[sqlite3.Connection], None],
    ) -> Callable[[sqlite3.Connection], None]:
        _MIGRATIONS.append((version, description, fn))
        return fn

    return decorator


def run_migrations(db_path: str) -> None:
    """Connect to *db_path* and apply any pending registered migrations.

    Must be called **after** ``init_db()`` so the base tables already exist.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version  INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()

        applied: set[int] = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        for version, description, fn in sorted(_MIGRATIONS, key=lambda m: m[0]):
            if version in applied:
                logger.debug("migration_already_applied", version=version)
                continue
            logger.info("migration_applying", version=version, description=description)
            fn(conn)
            conn.execute(
                "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?)",
                (version, description, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            logger.info("migration_applied", version=version, description=description)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Baseline migration (v1)
# ---------------------------------------------------------------------------
# This is a no-op because ``init_db()`` already creates the entire base schema
# on every startup. Future migrations will build on top of this baseline.
# When deploying to a database that already has the schema, this migration
# ensures the ``schema_migrations`` table exists and records v1 as applied.
# ---------------------------------------------------------------------------


@register(version=1, description="Baseline schema (handled by init_db)")
def _baseline_v1(conn: sqlite3.Connection) -> None:
    """Baseline migration — no structural changes needed.

    ``init_db()`` already handles initial table creation via
    ``CREATE TABLE IF NOT EXISTS``, so there is nothing for v1 to do. Its
    only purpose is to be recorded in ``schema_migrations`` so that future
    migrations build on a known starting point.
    """
    # Nothing to do — see docstring above.
    # If you are deploying to a fresh database, ``init_db()`` will run first
    # and create all tables. If you are deploying to an existing database,
    # the schema is already in place.


@register(version=2, description="Create api_keys table for AI provider key storage")
def _v2_api_keys(conn: sqlite3.Connection) -> None:
    """Create the ``api_keys`` table for encrypted AI provider keys."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            provider TEXT PRIMARY KEY,
            encrypted_key TEXT NOT NULL,
            label TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
