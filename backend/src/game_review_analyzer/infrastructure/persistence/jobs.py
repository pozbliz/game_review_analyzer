"""SQLite persistence and transitions for durable Analysis Jobs."""

from pathlib import Path
import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    insert_review_revisions,
)

JobState = Literal["queued", "running", "completed", "failed", "cancelled"]


class AnalysisJob(BaseModel):
    """Expose the durable state needed to run and present one review import."""

    id: str
    app_id: int
    scope: Literal["quick", "full", "refresh", "reconciliation"]
    state: JobState
    target_count: int
    imported_count: int
    cursor: str
    cancel_requested: bool
    error_code: str | None


class JobNotFound(Exception):
    """Tell callers that an Analysis Job identifier is not stored locally."""


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_job(database_path: Path, app_id: int, target_count: int) -> AnalysisJob:
    """Create and return one queued Quick import job."""

    job_id: str = str(uuid4())
    with connect(database_path) as connection:
        connection.execute(
            "INSERT INTO analysis_jobs(id, app_id, scope, state, target_count) "
            "VALUES (?, ?, 'quick', 'queued', ?)",
            (job_id, app_id, target_count),
        )
    return get_job(database_path, job_id)


def get_job(database_path: Path, job_id: str) -> AnalysisJob:
    """Return one durable job or raise JobNotFound."""

    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, app_id, scope, state, target_count, imported_count, cursor, "
            "cancel_requested, error_code FROM analysis_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
    if row is None:
        raise JobNotFound(job_id)
    return AnalysisJob(
        id=row[0],
        app_id=row[1],
        scope=row[2],
        state=row[3],
        target_count=row[4],
        imported_count=row[5],
        cursor=row[6],
        cancel_requested=bool(row[7]),
        error_code=row[8],
    )


def start_job(database_path: Path, job_id: str) -> AnalysisJob | None:
    """Atomically claim a queued job for one runner."""

    with connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE analysis_jobs SET state = 'running', updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND state = 'queued'",
            (job_id,),
        )
    return get_job(database_path, job_id) if cursor.rowcount else None


def request_cancellation(database_path: Path, job_id: str) -> None:
    """Cancel queued work immediately or signal a running job to stop."""

    with connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE analysis_jobs SET "
            "state = CASE WHEN state = 'queued' THEN 'cancelled' ELSE state END, "
            "cancel_requested = CASE WHEN state = 'running' THEN 1 ELSE cancel_requested END, "
            "updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND state IN ('queued', 'running')",
            (job_id,),
        )
    if cursor.rowcount == 0:
        get_job(database_path, job_id)


def cancellation_requested(database_path: Path, job_id: str) -> bool:
    """Return whether a running job has received a durable cancellation request."""

    return get_job(database_path, job_id).cancel_requested


def retry_job(database_path: Path, job_id: str) -> AnalysisJob:
    """Requeue failed or cancelled work from its latest checkpoint."""

    with connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE analysis_jobs SET state = 'queued', cancel_requested = 0, "
            "error_code = NULL, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND state IN ('failed', 'cancelled')",
            (job_id,),
        )
    if cursor.rowcount == 0:
        raise ValueError("Only failed or cancelled jobs can be retried")
    return get_job(database_path, job_id)


def recoverable_job_ids(database_path: Path) -> list[str]:
    """Requeue abandoned running jobs and return every queued job identifier."""

    with connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_jobs SET state = 'queued', updated_at = CURRENT_TIMESTAMP "
            "WHERE state = 'running'"
        )
        rows = connection.execute(
            "SELECT id FROM analysis_jobs WHERE state = 'queued' ORDER BY created_at, id"
        ).fetchall()
    return [row[0] for row in rows]


def checkpoint_page(
    database_path: Path,
    job_id: str,
    reviews: tuple[SteamReview, ...],
    next_cursor: str,
) -> AnalysisJob:
    """Persist one page and its progress in a single transaction."""

    with connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT app_id, imported_count FROM analysis_jobs "
            "WHERE id = ? AND state = 'running'",
            (job_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Job is not running")
        unique_reviews = tuple({review.review_id: review for review in reviews}.values())
        insert_review_revisions(connection, row[0], unique_reviews)
        imported_count: int = row[1] + len(unique_reviews)
        sequence: int = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM job_checkpoints WHERE job_id = ?",
            (job_id,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO job_checkpoints(job_id, sequence, cursor, imported_count) "
            "VALUES (?, ?, ?, ?)",
            (job_id, sequence, next_cursor, imported_count),
        )
        connection.execute(
            "UPDATE analysis_jobs SET imported_count = ?, cursor = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (imported_count, next_cursor, job_id),
        )
    return get_job(database_path, job_id)


def finish_job(database_path: Path, job_id: str, state: JobState, error_code: str | None = None) -> None:
    """Move a running job into one terminal state."""

    if state not in ("completed", "failed", "cancelled"):
        raise ValueError("finish_job requires a terminal state")
    with connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_jobs SET state = ?, error_code = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ? AND state = 'running'",
            (state, error_code, job_id),
        )
