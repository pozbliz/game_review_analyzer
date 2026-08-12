"""SQLite state for durable provider analysis runs."""

import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, computed_field

from game_review_analyzer.domain.reports import ThemeMetricPolicy
from game_review_analyzer.infrastructure.persistence.jobs import connect


class AnalysisRun(BaseModel):
    """Expose one exact provider run and its measured usage."""

    id: str
    app_id: int
    provider: str
    model: str
    state: Literal["queued", "running", "completed", "failed", "cancelled"]
    review_revision_ids: tuple[int, ...]
    metric_policy: ThemeMetricPolicy
    cancel_requested: bool
    error_code: str | None
    report_version_id: str | None
    input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None

    @computed_field
    @property
    def review_count(self) -> int:
        return len(self.review_revision_ids)


class AnalysisRunNotFound(Exception):
    """Tell callers that an analysis run is not stored locally."""


def create_analysis_run(
    database_path: Path,
    *,
    app_id: int,
    provider: str,
    model: str,
    metric_policy: ThemeMetricPolicy,
) -> AnalysisRun:
    """Queue a provider run over the latest immutable revision of every review."""

    with connect(database_path) as connection:
        revision_ids = tuple(
            row[0]
            for row in connection.execute(
                "SELECT review_revisions.id FROM review_revisions "
                "JOIN reviews ON reviews.id = review_revisions.review_id "
                "WHERE reviews.app_id = ? AND NOT EXISTS ("
                "SELECT 1 FROM review_revisions newer "
                "WHERE newer.review_id = review_revisions.review_id "
                "AND newer.id > review_revisions.id) ORDER BY review_revisions.id",
                (app_id,),
            )
        )
        if not revision_ids:
            raise ValueError("Analysis requires an existing review dataset")
        run_id = str(uuid4())
        connection.execute(
            "INSERT INTO analysis_runs("
            "id, app_id, provider, model, state, review_revision_ids_json, metric_policy_json"
            ") VALUES (?, ?, ?, ?, 'queued', ?, ?)",
            (
                run_id,
                app_id,
                provider,
                model,
                json.dumps(revision_ids),
                metric_policy.model_dump_json(),
            ),
        )
    return get_analysis_run(database_path, run_id)


def get_analysis_run(database_path: Path, run_id: str) -> AnalysisRun:
    """Load one durable provider run."""

    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, app_id, provider, model, state, review_revision_ids_json, "
            "metric_policy_json, cancel_requested, error_code, report_version_id, "
            "input_tokens, cached_input_tokens, output_tokens "
            "FROM analysis_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        raise AnalysisRunNotFound(run_id)
    return AnalysisRun(
        id=row[0], app_id=row[1], provider=row[2], model=row[3], state=row[4],
        review_revision_ids=tuple(json.loads(row[5])),
        metric_policy=ThemeMetricPolicy.model_validate_json(row[6]),
        cancel_requested=bool(row[7]), error_code=row[8], report_version_id=row[9],
        input_tokens=row[10], cached_input_tokens=row[11], output_tokens=row[12],
    )


def start_analysis_run(database_path: Path, run_id: str) -> AnalysisRun | None:
    """Atomically claim one queued provider run."""

    with connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE analysis_runs SET state = 'running', updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND state = 'queued'", (run_id,)
        )
    return get_analysis_run(database_path, run_id) if cursor.rowcount else None


def request_analysis_cancellation(database_path: Path, run_id: str) -> None:
    """Cancel queued work or signal a running provider process."""

    with connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE analysis_runs SET "
            "state = CASE WHEN state = 'queued' THEN 'cancelled' ELSE state END, "
            "cancel_requested = CASE WHEN state = 'running' THEN 1 ELSE cancel_requested END, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ? "
            "AND state IN ('queued', 'running')", (run_id,)
        )
    if cursor.rowcount == 0:
        get_analysis_run(database_path, run_id)


def finish_analysis_run(
    database_path: Path,
    run_id: str,
    state: Literal["completed", "failed", "cancelled"],
    *,
    error_code: str | None = None,
    report_version_id: str | None = None,
    input_tokens: int | None = None,
    cached_input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    """Persist one terminal provider outcome."""

    with connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_runs SET state = ?, error_code = ?, report_version_id = ?, "
            "input_tokens = ?, cached_input_tokens = ?, output_tokens = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ? AND state = 'running'",
            (state, error_code, report_version_id, input_tokens,
             cached_input_tokens, output_tokens, run_id),
        )


def recoverable_analysis_run_ids(database_path: Path) -> list[str]:
    """Requeue interrupted provider runs and return queued identifiers."""

    with connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_runs SET state = 'queued', updated_at = CURRENT_TIMESTAMP "
            "WHERE state = 'running'"
        )
        rows = connection.execute(
            "SELECT id FROM analysis_runs WHERE state = 'queued' ORDER BY created_at, id"
        ).fetchall()
    return [row[0] for row in rows]
