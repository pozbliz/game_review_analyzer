"""SQLite initialization and migration primitives."""

import sqlite3
from pathlib import Path


CURRENT_SCHEMA_VERSION = 2


def initialize_database(database_path: Path) -> None:
    """Create the database parent directory and apply all required migrations."""

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        applied_versions = {
            row[0] for row in connection.execute("SELECT version FROM schema_migrations")
        }
        if 1 not in applied_versions:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS application_metadata "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (1)")
        if 2 not in applied_versions:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS game_datasets ("
                "app_id INTEGER PRIMARY KEY CHECK (app_id > 0), "
                "metadata_json TEXT NOT NULL, "
                "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (2)")


def schema_version(database_path: Path) -> int:
    """Return the highest applied schema version, or zero for an uninitialized database."""

    if not database_path.exists():
        return 0
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()
    return int(row[0] or 0)
