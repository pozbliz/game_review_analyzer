"""Integrity tests for reviews, immutable revisions, jobs, and checkpoints."""

from pathlib import Path
import sqlite3

import pytest

from game_review_analyzer.infrastructure.persistence.database import (
    CURRENT_SCHEMA_VERSION,
    initialize_database,
    schema_version,
)


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def test_review_import_schema_enforces_ownership_and_valid_states(tmp_path: Path) -> None:
    database_path = tmp_path / "app.sqlite3"
    initialize_database(database_path)

    assert CURRENT_SCHEMA_VERSION == 3
    assert schema_version(database_path) == 3

    with connect(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO reviews(id, app_id) VALUES ('review-1', 1145350)"
            )

        connection.execute(
            "INSERT INTO game_datasets(app_id, metadata_json) VALUES (1145350, '{}')"
        )
        connection.execute(
            "INSERT INTO reviews(id, app_id) VALUES ('review-1', 1145350)"
        )
        connection.execute(
            "INSERT INTO review_revisions(review_id, source_updated_at, content_hash, content_json) "
            "VALUES ('review-1', 1, 'hash', '{}')"
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO analysis_jobs(id, app_id, scope, state, target_count) "
                "VALUES ('job-1', 1145350, 'quick', 'not-a-state', 100)"
            )
        connection.execute(
            "INSERT INTO analysis_jobs(id, app_id, scope, state, target_count) "
            "VALUES ('job-1', 1145350, 'quick', 'queued', 100)"
        )
        connection.execute(
            "INSERT INTO job_checkpoints(job_id, sequence, cursor, imported_count) "
            "VALUES ('job-1', 1, 'next', 10)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO job_checkpoints(job_id, sequence, cursor, imported_count) "
                "VALUES ('missing-job', 1, 'next', 10)"
            )
