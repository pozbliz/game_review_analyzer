"""SQLite state for durable provider analysis runs."""

import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, computed_field

from game_review_analyzer.domain.reports import ThemeMetricPolicy
from game_review_analyzer.infrastructure.persistence.jobs import connect


MAIN_REPORT_BATCH_CHARACTER_LIMIT = 32_000


class AnalysisRun(BaseModel):
    """Expose one exact provider run and its measured usage."""

    id: str
    app_id: int
    provider: str
    model: str
    state: Literal["queued", "running", "completed", "failed", "cancelled"]
    review_revision_ids: tuple[int, ...]
    early_review_revision_ids: tuple[int, ...]
    recent_review_revision_ids: tuple[int, ...]
    metric_policy: ThemeMetricPolicy
    cancel_requested: bool
    error_code: str | None
    report_version_id: str | None
    input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None
    extracted_review_count: int
    report_kind: Literal["main", "test"] | None
    oversized_review_count: int

    @computed_field
    @property
    def review_count(self) -> int:
        return len(self.review_revision_ids)

    @computed_field
    @property
    def phase(self) -> Literal["queued", "analyzing", "extracting", "consolidating", "completed", "failed", "cancelled"]:
        if self.state != "running":
            return self.state
        if self.report_kind == "test":
            return "analyzing"
        return (
            "consolidating"
            if self.extracted_review_count >= self.review_count
            else "extracting"
        )


class AnalysisRunNotFound(Exception):
    """Tell callers that an analysis run is not stored locally."""


class FullHistoryRequired(ValueError):
    """Require a completed Full import before chronological cohort selection."""


def create_analysis_run(
    database_path: Path,
    *,
    app_id: int,
    provider: str,
    model: str,
    metric_policy: ThemeMetricPolicy,
    cohort_size: int = 2_500,
    report_kind: Literal["main", "test"] | None = None,
) -> AnalysisRun:
    """Queue a provider run over non-overlapping oldest and newest review cohorts."""

    if not 1 <= cohort_size <= 2_500:
        raise ValueError("Cohort size must be between 1 and 2,500")

    with connect(database_path) as connection:
        completed_full_import: tuple[int] | None = connection.execute(
            "SELECT 1 FROM analysis_jobs WHERE app_id = ? AND scope = 'full' "
            "AND state = 'completed' LIMIT 1",
            (app_id,),
        ).fetchone()
        if completed_full_import is None:
            raise FullHistoryRequired(
                "Analysis requires a completed full-history import"
            )
        ordered_revisions: tuple[tuple[int, str], ...] = tuple(
            (int(row[0]), str(row[1]))
            for row in connection.execute(
                "SELECT review_revisions.id, review_revisions.content_json "
                "FROM review_revisions "
                "JOIN reviews ON reviews.id = review_revisions.review_id "
                "WHERE reviews.app_id = ? AND NOT EXISTS ("
                "SELECT 1 FROM review_revisions newer "
                "WHERE newer.review_id = review_revisions.review_id "
                "AND newer.id > review_revisions.id) "
                "ORDER BY json_extract(review_revisions.content_json, '$.source_created_at'), "
                "reviews.id, review_revisions.id",
                (app_id,),
            )
        )
        ordered_revision_ids: tuple[int, ...] = tuple(
            revision_id
            for revision_id, content_json in ordered_revisions
            if report_kind != "main"
            or len(str(json.loads(content_json)["text"]))
            <= MAIN_REPORT_BATCH_CHARACTER_LIMIT
        )
        oversized_review_count: int = len(ordered_revisions) - len(ordered_revision_ids)
        if not ordered_revision_ids:
            raise ValueError("Analysis requires an existing review dataset")
        if len(ordered_revision_ids) <= cohort_size * 2:
            midpoint: int = len(ordered_revision_ids) // 2
            early_revision_ids: tuple[int, ...] = ordered_revision_ids[:midpoint]
            recent_revision_ids: tuple[int, ...] = ordered_revision_ids[midpoint:]
        else:
            early_revision_ids = ordered_revision_ids[:cohort_size]
            recent_revision_ids = ordered_revision_ids[-cohort_size:]
        revision_ids: tuple[int, ...] = early_revision_ids + recent_revision_ids
        run_id = str(uuid4())
        connection.execute(
            "INSERT INTO analysis_runs("
            "id, app_id, provider, model, state, review_revision_ids_json, "
            "early_review_revision_ids_json, recent_review_revision_ids_json, "
            "metric_policy_json, report_kind, oversized_review_count) "
            "VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                app_id,
                provider,
                model,
                json.dumps(revision_ids),
                json.dumps(early_revision_ids),
                json.dumps(recent_revision_ids),
                metric_policy.model_dump_json(),
                report_kind,
                oversized_review_count,
            ),
        )
    return get_analysis_run(database_path, run_id)


def get_analysis_run(database_path: Path, run_id: str) -> AnalysisRun:
    """Load one durable provider run."""

    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, app_id, provider, model, state, review_revision_ids_json, "
            "metric_policy_json, cancel_requested, error_code, report_version_id, "
            "input_tokens, cached_input_tokens, output_tokens, "
            "early_review_revision_ids_json, recent_review_revision_ids_json, "
            "report_kind, oversized_review_count, "
            "CASE WHEN report_kind = 'main' THEN COALESCE(("
            "SELECT SUM(json_array_length(json_extract(batch.result_json, "
            "'$.completed_review_revision_ids'))) FROM analysis_theme_batches batch "
            "WHERE batch.run_id = analysis_runs.id), 0) ELSE ("
            "SELECT COUNT(*) FROM review_opinion_extractions extraction "
            "WHERE extraction.provider = analysis_runs.provider "
            "AND extraction.model = analysis_runs.model "
            "AND extraction.contract_version = '1.0' "
            "AND extraction.review_revision_id IN ("
            "SELECT value FROM json_each(analysis_runs.review_revision_ids_json))) END "
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
        early_review_revision_ids=tuple(json.loads(row[13])),
        recent_review_revision_ids=tuple(json.loads(row[14])),
        report_kind=row[15],
        oversized_review_count=int(row[16]),
        extracted_review_count=int(row[17]),
    )


def load_latest_analysis_run(database_path: Path, app_id: int) -> AnalysisRun | None:
    """Load the newest durable analysis run for one game."""

    with connect(database_path) as connection:
        row: tuple[str] | None = connection.execute(
            "SELECT id FROM analysis_runs WHERE app_id = ? "
            "ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (app_id,),
        ).fetchone()
    return get_analysis_run(database_path, row[0]) if row else None


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


def retry_analysis_run(database_path: Path, run_id: str) -> AnalysisRun:
    """Requeue failed or cancelled analysis while retaining safe cached extraction."""

    with connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE analysis_runs SET state = 'queued', cancel_requested = 0, "
            "error_code = NULL, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND state IN ('failed', 'cancelled')",
            (run_id,),
        )
    if cursor.rowcount == 0:
        raise ValueError("Only failed or cancelled analysis can be retried")
    return get_analysis_run(database_path, run_id)
