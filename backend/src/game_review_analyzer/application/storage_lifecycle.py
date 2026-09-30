"""Inspect and explicitly delete locally owned application data."""

from pathlib import Path
import sqlite3

from pydantic import BaseModel


class StorageDiagnostics(BaseModel):
    """Expose local database location, size, and retained ownership counts."""

    database_path: str
    database_bytes: int
    game_dataset_count: int
    report_version_count: int
    review_revision_count: int
    incomplete_job_count: int


class DatabaseIntegrity(BaseModel):
    """Summarize SQLite and application-ownership integrity checks."""

    sqlite_ok: bool
    foreign_key_violations: int
    orphan_count: int


def connect(database_path: Path) -> sqlite3.Connection:
    """Open one foreign-key-enforcing lifecycle transaction."""

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_storage_diagnostics(database_path: Path) -> StorageDiagnostics:
    """Measure retained SQLite files and high-level record counts."""

    related_files: tuple[Path, ...] = (
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    )
    database_bytes: int = sum(
        path.stat().st_size for path in related_files if path.exists()
    )
    with connect(database_path) as connection:
        counts: tuple[int, int, int, int] = (
            connection.execute("SELECT COUNT(*) FROM game_datasets").fetchone()[0],
            connection.execute("SELECT COUNT(*) FROM report_versions").fetchone()[0],
            connection.execute("SELECT COUNT(*) FROM review_revisions").fetchone()[0],
            connection.execute(
                "SELECT COUNT(*) FROM analysis_jobs WHERE state != 'completed'"
            ).fetchone()[0],
        )
    return StorageDiagnostics(
        database_path=str(database_path.resolve()),
        database_bytes=database_bytes,
        game_dataset_count=counts[0],
        report_version_count=counts[1],
        review_revision_count=counts[2],
        incomplete_job_count=counts[3],
    )


def delete_report_version(
    database_path: Path, report_version_id: str, confirmation: str
) -> None:
    """Delete one report only after its exact identifier is repeated."""

    require_confirmation(report_version_id, confirmation)
    with connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_runs SET report_version_id = NULL "
            "WHERE report_version_id = ?",
            (report_version_id,),
        )
        cursor = connection.execute(
            "DELETE FROM report_versions WHERE id = ?", (report_version_id,)
        )
    if cursor.rowcount == 0:
        raise ValueError("Report Version is unavailable")


def delete_incomplete_job(
    database_path: Path, job_id: str, confirmation: str
) -> None:
    """Delete one inactive incomplete job after exact identifier confirmation."""

    require_confirmation(job_id, confirmation)
    with connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM analysis_jobs WHERE id = ? "
            "AND state IN ('queued', 'failed', 'cancelled')",
            (job_id,),
        )
    if cursor.rowcount == 0:
        raise ValueError("Only inactive incomplete jobs can be deleted")


def delete_game_dataset(
    database_path: Path, app_id: int, confirmation: str
) -> None:
    """Delete a complete Game Dataset ownership tree after strong confirmation."""

    require_confirmation(f"DELETE {app_id}", confirmation)
    with connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        active_jobs: int = connection.execute(
            "SELECT COUNT(*) FROM analysis_jobs WHERE app_id = ? "
            "AND state IN ('queued', 'running')",
            (app_id,),
        ).fetchone()[0]
        if active_jobs:
            raise ValueError("Cancel active jobs before deleting the Game Dataset")
        cursor = connection.execute(
            "DELETE FROM game_datasets WHERE app_id = ?", (app_id,)
        )
    if cursor.rowcount == 0:
        raise ValueError("Game Dataset is unavailable")


def require_confirmation(expected: str, actual: str) -> None:
    """Reject destructive requests whose confirmation is not exact."""

    if actual != expected:
        raise ValueError("Exact deletion confirmation is required")


def verify_database_integrity(database_path: Path) -> DatabaseIntegrity:
    """Check SQLite constraints plus every application ownership relationship."""

    orphan_queries: tuple[str, ...] = (
        "SELECT COUNT(*) FROM reviews LEFT JOIN game_datasets "
        "ON game_datasets.app_id = reviews.app_id WHERE game_datasets.app_id IS NULL",
        "SELECT COUNT(*) FROM review_revisions LEFT JOIN reviews "
        "ON reviews.id = review_revisions.review_id WHERE reviews.id IS NULL",
        "SELECT COUNT(*) FROM analysis_jobs LEFT JOIN game_datasets "
        "ON game_datasets.app_id = analysis_jobs.app_id WHERE game_datasets.app_id IS NULL",
        "SELECT COUNT(*) FROM job_checkpoints LEFT JOIN analysis_jobs "
        "ON analysis_jobs.id = job_checkpoints.job_id WHERE analysis_jobs.id IS NULL",
        "SELECT COUNT(*) FROM job_analysis_scopes LEFT JOIN analysis_jobs "
        "ON analysis_jobs.id = job_analysis_scopes.job_id WHERE analysis_jobs.id IS NULL",
        "SELECT COUNT(*) FROM report_versions LEFT JOIN game_datasets "
        "ON game_datasets.app_id = report_versions.app_id WHERE game_datasets.app_id IS NULL",
        "SELECT COUNT(*) FROM report_version_review_revisions AS bindings "
        "LEFT JOIN report_versions ON report_versions.id = bindings.report_version_id "
        "LEFT JOIN review_revisions ON review_revisions.id = bindings.review_revision_id "
        "WHERE report_versions.id IS NULL OR review_revisions.id IS NULL",
        "SELECT COUNT(*) FROM job_seen_reviews AS seen "
        "LEFT JOIN analysis_jobs ON analysis_jobs.id = seen.job_id "
        "LEFT JOIN reviews ON reviews.id = seen.review_id "
        "WHERE analysis_jobs.id IS NULL OR reviews.id IS NULL",
        "SELECT COUNT(*) FROM reconciliation_results LEFT JOIN analysis_jobs "
        "ON analysis_jobs.id = reconciliation_results.job_id "
        "WHERE analysis_jobs.id IS NULL",
    )
    with connect(database_path) as connection:
        sqlite_ok: bool = connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        foreign_key_violations: int = len(
            connection.execute("PRAGMA foreign_key_check").fetchall()
        )
        orphan_count: int = sum(
            connection.execute(query).fetchone()[0] for query in orphan_queries
        )
    return DatabaseIntegrity(
        sqlite_ok=sqlite_ok,
        foreign_key_violations=foreign_key_violations,
        orphan_count=orphan_count,
    )
