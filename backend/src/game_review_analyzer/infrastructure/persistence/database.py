"""SQLite initialization and migration primitives."""

import sqlite3
from pathlib import Path


CURRENT_SCHEMA_VERSION = 4


def initialize_database(database_path: Path) -> None:
    """Create the database parent directory and apply all required migrations."""

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
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
        if 3 not in applied_versions:
            connection.execute(
                "CREATE TABLE reviews ("
                "id TEXT PRIMARY KEY, "
                "app_id INTEGER NOT NULL REFERENCES game_datasets(app_id) ON DELETE CASCADE)"
            )
            connection.execute(
                "CREATE TABLE review_revisions ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE, "
                "source_updated_at INTEGER NOT NULL, "
                "content_hash TEXT NOT NULL, "
                "content_json TEXT NOT NULL, "
                "observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(review_id, source_updated_at, content_hash))"
            )
            connection.execute(
                "CREATE TABLE analysis_jobs ("
                "id TEXT PRIMARY KEY, "
                "app_id INTEGER NOT NULL REFERENCES game_datasets(app_id) ON DELETE CASCADE, "
                "scope TEXT NOT NULL CHECK (scope IN ('quick', 'full', 'refresh', 'reconciliation')), "
                "state TEXT NOT NULL CHECK (state IN "
                "('queued', 'running', 'completed', 'failed', 'cancelled')), "
                "target_count INTEGER NOT NULL CHECK (target_count > 0), "
                "imported_count INTEGER NOT NULL DEFAULT 0 CHECK (imported_count >= 0), "
                "cursor TEXT NOT NULL DEFAULT '*', "
                "cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK (cancel_requested IN (0, 1)), "
                "error_code TEXT, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "CREATE TABLE job_checkpoints ("
                "job_id TEXT NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE, "
                "sequence INTEGER NOT NULL CHECK (sequence > 0), "
                "cursor TEXT NOT NULL, "
                "imported_count INTEGER NOT NULL CHECK (imported_count >= 0), "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "PRIMARY KEY(job_id, sequence))"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (3)")
        if 4 not in applied_versions:
            connection.execute(
                "CREATE TABLE report_versions ("
                "id TEXT PRIMARY KEY, "
                "app_id INTEGER NOT NULL REFERENCES game_datasets(app_id) ON DELETE CASCADE, "
                "snapshot_json TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "CREATE TABLE report_version_review_revisions ("
                "report_version_id TEXT NOT NULL "
                "REFERENCES report_versions(id) ON DELETE CASCADE, "
                "review_revision_id INTEGER NOT NULL "
                "REFERENCES review_revisions(id) ON DELETE RESTRICT, "
                "PRIMARY KEY(report_version_id, review_revision_id))"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (4)")


def schema_version(database_path: Path) -> int:
    """Return the highest applied schema version, or zero for an uninitialized database."""

    if not database_path.exists():
        return 0
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()
    return int(row[0] or 0)
