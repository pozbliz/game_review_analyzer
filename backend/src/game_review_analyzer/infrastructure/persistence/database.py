"""SQLite initialization and migration primitives."""

import json
import sqlite3
from pathlib import Path


CURRENT_SCHEMA_VERSION = 13


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
        if 5 not in applied_versions:
            rows: list[tuple[str, str, str]] = connection.execute(
                "SELECT report_versions.id, report_versions.snapshot_json, "
                "game_datasets.metadata_json FROM report_versions "
                "JOIN game_datasets ON game_datasets.app_id = report_versions.app_id"
            ).fetchall()
            for report_id, snapshot_json, metadata_json in rows:
                snapshot: dict[str, object] = json.loads(snapshot_json)
                snapshot["schema_version"] = "2.0"
                snapshot.setdefault("metadata_snapshot", json.loads(metadata_json))
                connection.execute(
                    "UPDATE report_versions SET snapshot_json = ? WHERE id = ?",
                    (json.dumps(snapshot, separators=(",", ":")), report_id),
                )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (5)")
        if 6 not in applied_versions:
            connection.execute(
                "CREATE TABLE job_analysis_scopes ("
                "job_id TEXT PRIMARY KEY REFERENCES analysis_jobs(id) ON DELETE CASCADE, "
                "review_revision_ids_json TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (6)")
        if 7 not in applied_versions:
            connection.execute(
                "CREATE TABLE job_seen_reviews ("
                "job_id TEXT NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE, "
                "review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE, "
                "PRIMARY KEY(job_id, review_id))"
            )
            connection.execute(
                "CREATE TABLE reconciliation_results ("
                "job_id TEXT PRIMARY KEY REFERENCES analysis_jobs(id) ON DELETE CASCADE, "
                "app_id INTEGER NOT NULL REFERENCES game_datasets(app_id) ON DELETE CASCADE, "
                "present_review_count INTEGER NOT NULL CHECK (present_review_count >= 0), "
                "missing_review_ids_json TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (7)")
        if 8 not in applied_versions:
            connection.execute(
                "CREATE TABLE steam_catalog_games ("
                "app_id INTEGER PRIMARY KEY CHECK (app_id > 0), "
                "name TEXT NOT NULL CHECK (length(name) > 0), "
                "last_modified INTEGER NOT NULL CHECK (last_modified >= 0), "
                "price_change_number INTEGER NOT NULL CHECK (price_change_number >= 0))"
            )
            connection.execute(
                "CREATE TABLE steam_catalog_state ("
                "id INTEGER PRIMARY KEY CHECK (id = 1), "
                "synced_at INTEGER NOT NULL CHECK (synced_at >= 0))"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (8)")
        if 9 not in applied_versions:
            connection.execute(
                "CREATE TABLE analysis_runs ("
                "id TEXT PRIMARY KEY, "
                "app_id INTEGER NOT NULL REFERENCES game_datasets(app_id) ON DELETE CASCADE, "
                "provider TEXT NOT NULL CHECK (length(provider) > 0), "
                "model TEXT NOT NULL CHECK (length(model) > 0), "
                "state TEXT NOT NULL CHECK (state IN "
                "('queued', 'running', 'completed', 'failed', 'cancelled')), "
                "review_revision_ids_json TEXT NOT NULL, "
                "metric_policy_json TEXT NOT NULL, "
                "cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK (cancel_requested IN (0, 1)), "
                "error_code TEXT, report_version_id TEXT REFERENCES report_versions(id), "
                "input_tokens INTEGER CHECK (input_tokens >= 0), "
                "cached_input_tokens INTEGER CHECK (cached_input_tokens >= 0), "
                "output_tokens INTEGER CHECK (output_tokens >= 0), "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (9)")
        if 10 not in applied_versions:
            connection.execute(
                "ALTER TABLE analysis_runs ADD COLUMN "
                "early_review_revision_ids_json TEXT NOT NULL DEFAULT '[]'"
            )
            connection.execute(
                "ALTER TABLE analysis_runs ADD COLUMN "
                "recent_review_revision_ids_json TEXT NOT NULL DEFAULT '[]'"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (10)")
        if 11 not in applied_versions:
            connection.execute(
                "CREATE TABLE review_opinion_extractions ("
                "review_revision_id INTEGER NOT NULL "
                "REFERENCES review_revisions(id) ON DELETE CASCADE, "
                "provider TEXT NOT NULL, model TEXT NOT NULL, "
                "contract_version TEXT NOT NULL, opinion_points_json TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "PRIMARY KEY(review_revision_id, provider, model, contract_version))"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (11)")
        if 12 not in applied_versions:
            connection.execute(
                "ALTER TABLE report_versions ADD COLUMN report_kind TEXT "
                "CHECK (report_kind IN ('main', 'test'))"
            )
            connection.execute(
                "CREATE UNIQUE INDEX report_versions_current_slot "
                "ON report_versions(app_id, report_kind) WHERE report_kind IS NOT NULL"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (12)")
        if 13 not in applied_versions:
            connection.execute(
                "ALTER TABLE analysis_runs ADD COLUMN report_kind TEXT "
                "CHECK (report_kind IN ('main', 'test'))"
            )
            connection.execute("INSERT INTO schema_migrations(version) VALUES (13)")


def schema_version(database_path: Path) -> int:
    """Return the highest applied schema version, or zero for an uninitialized database."""

    if not database_path.exists():
        return 0
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()
    return int(row[0] or 0)
