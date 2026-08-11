"""Storage diagnostics, confirmed deletion, and orphan-integrity tests."""

from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from game_review_analyzer.application.storage_lifecycle import (
    delete_game_dataset,
    delete_incomplete_job,
    delete_report_version,
    get_storage_diagnostics,
    verify_database_integrity,
)
from game_review_analyzer.infrastructure.persistence.jobs import (
    JobNotFound,
    create_job,
    get_job,
    request_cancellation,
)
from game_review_analyzer.infrastructure.persistence.report_versions import load_report_version
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from tests.integration.test_report_api import seed_report


def test_storage_diagnostics_and_individually_confirmed_deletions(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "data" / "app.sqlite3"
    seed_report(database_path)
    job = create_job(database_path, 1145350, 10)

    diagnostics = get_storage_diagnostics(database_path)
    assert diagnostics.database_path == str(database_path.resolve())
    assert diagnostics.database_bytes > 0
    assert diagnostics.game_dataset_count == 1
    assert diagnostics.report_version_count == 1
    assert diagnostics.review_revision_count == 2
    assert diagnostics.incomplete_job_count == 1

    with pytest.raises(ValueError, match="confirmation"):
        delete_report_version(database_path, "report-1", "wrong")
    assert load_report_version(database_path, "report-1") is not None
    delete_report_version(database_path, "report-1", "report-1")
    assert load_report_version(database_path, "report-1") is None

    with pytest.raises(ValueError, match="confirmation"):
        delete_incomplete_job(database_path, job.id, "wrong")
    delete_incomplete_job(database_path, job.id, job.id)
    with pytest.raises(JobNotFound):
        get_job(database_path, job.id)
    assert verify_database_integrity(database_path).orphan_count == 0


def test_confirmed_game_dataset_deletion_cascades_all_owned_state(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)
    job = create_job(database_path, 1145350, 10)
    request_cancellation(database_path, job.id)

    with pytest.raises(ValueError, match="confirmation"):
        delete_game_dataset(database_path, 1145350, "1145350")
    delete_game_dataset(database_path, 1145350, "DELETE 1145350")

    with sqlite3.connect(database_path) as connection:
        for table in (
            "game_datasets",
            "reviews",
            "review_revisions",
            "analysis_jobs",
            "report_versions",
            "report_version_review_revisions",
        ):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    integrity = verify_database_integrity(database_path)
    assert integrity.foreign_key_violations == 0
    assert integrity.orphan_count == 0


def test_storage_and_confirmed_deletion_http_contract(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)

    with TestClient(create_app(Settings(database_path=database_path))) as client:
        diagnostics = client.get("/api/storage")
        rejected = client.post(
            "/api/reports/report-1/delete", json={"confirmation": "wrong"}
        )
        deleted = client.post(
            "/api/reports/report-1/delete", json={"confirmation": "report-1"}
        )
        integrity = client.get("/api/storage/integrity")

    assert diagnostics.status_code == 200
    assert diagnostics.json()["database_path"] == str(database_path.resolve())
    assert rejected.status_code == 409
    assert deleted.status_code == 204
    assert integrity.json() == {
        "sqlite_ok": True,
        "foreign_key_violations": 0,
        "orphan_count": 0,
    }


def test_game_dataset_deletion_rejects_an_active_job(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)
    job = create_job(database_path, 1145350, 10)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_jobs SET state = 'running' WHERE id = ?", (job.id,)
        )

    with pytest.raises(ValueError, match="active jobs"):
        delete_game_dataset(database_path, 1145350, "DELETE 1145350")
    assert load_report_version(database_path, "report-1") is not None
