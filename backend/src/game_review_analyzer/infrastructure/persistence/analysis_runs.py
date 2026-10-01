"""SQLite state for durable provider analysis runs."""

import json
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, computed_field

from game_review_analyzer.domain.reports import AggregateReport, ThemeMetricPolicy
from game_review_analyzer.infrastructure.persistence.jobs import connect, insert_refresh_job


MAIN_REPORT_BATCH_CHARACTER_LIMIT = 32_000
AnalysisOperation = Literal["create", "extend", "replace", "test"]


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
    operation: AnalysisOperation | None
    base_report_id: str | None
    refresh_job_id: str | None

    @computed_field
    @property
    def review_count(self) -> int:
        return len(self.review_revision_ids)

    @computed_field
    @property
    def phase(self) -> Literal["queued", "refreshing", "analyzing", "extracting", "consolidating", "completed", "failed", "cancelled"]:
        if self.state != "running":
            return self.state
        if self.refresh_job_id is not None and not self.review_revision_ids:
            return "refreshing"
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


class AnalysisReservationConflict(ValueError):
    """Reject a second active run for one report slot."""


class NoUnseenReviews(ValueError):
    """Tell callers that an extension has no usable unseen identities."""


def create_analysis_run(
    database_path: Path,
    *,
    app_id: int,
    provider: str,
    model: str,
    metric_policy: ThemeMetricPolicy,
    cohort_size: int = 2_500,
    report_kind: Literal["main", "test"] | None = None,
    excluded_revision_ids: tuple[int, ...] = (),
    operation: AnalysisOperation | None = None,
) -> AnalysisRun:
    """Queue a provider run over non-overlapping oldest and newest review cohorts."""

    if not 1 <= cohort_size <= 2_500:
        raise ValueError("Cohort size must be between 1 and 2,500")

    try:
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
            early_revision_ids, recent_revision_ids, oversized_review_count = (
                _select_analysis_scope(
                    connection,
                    app_id=app_id,
                    cohort_size=cohort_size,
                    filter_oversized=report_kind is not None,
                    excluded_revision_ids=excluded_revision_ids,
                )
            )
            revision_ids: tuple[int, ...] = early_revision_ids + recent_revision_ids
            run_id: str = str(uuid4())
            connection.execute(
                "INSERT INTO analysis_runs("
                "id, app_id, provider, model, state, review_revision_ids_json, "
                "early_review_revision_ids_json, recent_review_revision_ids_json, "
                "metric_policy_json, report_kind, oversized_review_count, operation, "
                "base_report_id, refresh_job_id) "
                "VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
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
                    operation,
                ),
            )
    except sqlite3.IntegrityError as error:
        if "analysis_runs.app_id, analysis_runs.report_kind" in str(error):
            raise AnalysisReservationConflict(
                "Another analysis already reserves this report slot"
            ) from error
        raise
    return get_analysis_run(database_path, run_id)


def create_refresh_analysis_run(
    database_path: Path,
    *,
    app_id: int,
    provider: str,
    model: str,
    metric_policy: ThemeMetricPolicy,
    operation: Literal["extend", "replace"],
    base_report_id: str,
) -> AnalysisRun:
    """Atomically reserve the Main Report slot and its durable refresh job."""

    run_id: str = str(uuid4())
    try:
        with connect(database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            refresh_job_id: str = insert_refresh_job(connection, app_id, 5_000)
            connection.execute(
                "INSERT INTO analysis_runs("
                "id, app_id, provider, model, state, review_revision_ids_json, "
                "early_review_revision_ids_json, recent_review_revision_ids_json, "
                "metric_policy_json, report_kind, operation, base_report_id, refresh_job_id) "
                "VALUES (?, ?, ?, ?, 'queued', '[]', '[]', '[]', ?, 'main', ?, ?, ?)",
                (
                    run_id,
                    app_id,
                    provider,
                    model,
                    metric_policy.model_dump_json(),
                    operation,
                    base_report_id,
                    refresh_job_id,
                ),
            )
    except sqlite3.IntegrityError as error:
        if "analysis_runs.app_id, analysis_runs.report_kind" in str(error):
            raise AnalysisReservationConflict(
                "Another analysis already reserves this report slot"
            ) from error
        raise
    return get_analysis_run(database_path, run_id)


def reserve_refreshed_analysis_scope(
    database_path: Path,
    run_id: str,
    cohort_size: int = 500,
) -> AnalysisRun:
    """Reserve one exact post-refresh scope before provider work begins."""

    with connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT app_id, operation, base_report_id, refresh_job_id, "
            "review_revision_ids_json FROM analysis_runs "
            "WHERE id = ? AND state = 'running'",
            (run_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Analysis run is not running")
        if json.loads(row[4]):
            connection.commit()
            return get_analysis_run(database_path, run_id)
        scope_row = connection.execute(
            "SELECT review_revision_ids_json FROM job_analysis_scopes WHERE job_id = ?",
            (row[3],),
        ).fetchone()
        if scope_row is None:
            raise ValueError("Refresh scope is unavailable")
        report_row = connection.execute(
            "SELECT id, snapshot_json FROM report_versions "
            "WHERE app_id = ? AND report_kind = 'main'",
            (row[0],),
        ).fetchone()
        if report_row is None or report_row[0] != row[2]:
            raise ValueError("Base Main Report changed during analysis")
        report = AggregateReport.model_validate_json(report_row[1])
        excluded_revision_ids: tuple[int, ...] = (
            report.review_revision_ids if row[1] == "extend" else ()
        )
        early_ids, recent_ids, oversized_count = _select_analysis_scope(
            connection,
            app_id=int(row[0]),
            cohort_size=cohort_size,
            filter_oversized=True,
            excluded_revision_ids=excluded_revision_ids,
            available_revision_ids=tuple(json.loads(scope_row[0])),
        )
        revision_ids: tuple[int, ...] = early_ids + recent_ids
        connection.execute(
            "UPDATE analysis_runs SET review_revision_ids_json = ?, "
            "early_review_revision_ids_json = ?, recent_review_revision_ids_json = ?, "
            "oversized_review_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (
                json.dumps(revision_ids),
                json.dumps(early_ids),
                json.dumps(recent_ids),
                oversized_count,
                run_id,
            ),
        )
    return get_analysis_run(database_path, run_id)


def _select_analysis_scope(
    connection: sqlite3.Connection,
    *,
    app_id: int,
    cohort_size: int,
    filter_oversized: bool,
    excluded_revision_ids: tuple[int, ...] = (),
    available_revision_ids: tuple[int, ...] | None = None,
) -> tuple[tuple[int, ...], tuple[int, ...], int]:
    excluded_review_ids: set[str] = set()
    if excluded_revision_ids:
        placeholders: str = ",".join("?" for _ in excluded_revision_ids)
        excluded_review_ids = {
            str(row[0])
            for row in connection.execute(
                "SELECT review_id FROM review_revisions "
                f"WHERE id IN ({placeholders})",
                excluded_revision_ids,
            )
        }
    if available_revision_ids is None:
        rows = connection.execute(
            "SELECT review_revisions.id, review_revisions.content_json, reviews.id "
            "FROM review_revisions JOIN reviews ON reviews.id = review_revisions.review_id "
            "WHERE reviews.app_id = ? AND NOT EXISTS ("
            "SELECT 1 FROM review_revisions newer "
            "WHERE newer.review_id = review_revisions.review_id "
            "AND newer.id > review_revisions.id) "
            "ORDER BY json_extract(review_revisions.content_json, "
            "'$.source_created_at'), reviews.id, review_revisions.id",
            (app_id,),
        )
    else:
        placeholders = ",".join("?" for _ in available_revision_ids)
        rows = connection.execute(
            "SELECT review_revisions.id, review_revisions.content_json, reviews.id "
            "FROM review_revisions JOIN reviews ON reviews.id = review_revisions.review_id "
            f"WHERE reviews.app_id = ? AND review_revisions.id IN ({placeholders}) "
            "ORDER BY json_extract(review_revisions.content_json, "
            "'$.source_created_at'), reviews.id, review_revisions.id",
            (app_id, *available_revision_ids),
        )
    ordered_revisions: tuple[tuple[int, str], ...] = tuple(
        (int(row[0]), str(row[1]))
        for row in rows
        if str(row[2]) not in excluded_review_ids
    )
    eligible_by_id: dict[int, bool] = {
        revision_id: (
            not filter_oversized
            or len(str(json.loads(content_json)["text"]))
            <= MAIN_REPORT_BATCH_CHARACTER_LIMIT
        )
        for revision_id, content_json in ordered_revisions
    }
    eligible_ids: tuple[int, ...] = tuple(
        revision_id
        for revision_id, _ in ordered_revisions
        if eligible_by_id[revision_id]
    )
    if not eligible_ids:
        if excluded_revision_ids:
            raise NoUnseenReviews("No usable unseen reviews remain")
        raise ValueError("Analysis requires an existing review dataset")
    if len(eligible_ids) <= cohort_size * 2:
        midpoint: int = len(eligible_ids) // 2
        return (
            eligible_ids[:midpoint],
            eligible_ids[midpoint:],
            len(ordered_revisions) - len(eligible_ids) if filter_oversized else 0,
        )
    if not filter_oversized:
        return eligible_ids[:cohort_size], eligible_ids[-cohort_size:], 0
    early_list: list[int] = []
    skipped_ids: set[int] = set()
    for revision_id, _ in ordered_revisions:
        if eligible_by_id[revision_id]:
            early_list.append(revision_id)
            if len(early_list) == cohort_size:
                break
        else:
            skipped_ids.add(revision_id)
    recent_list: list[int] = []
    early_ids: set[int] = set(early_list)
    for revision_id, _ in reversed(ordered_revisions):
        if revision_id in early_ids:
            continue
        if eligible_by_id[revision_id]:
            recent_list.append(revision_id)
            if len(recent_list) == cohort_size:
                break
        else:
            skipped_ids.add(revision_id)
    return tuple(early_list), tuple(reversed(recent_list)), len(skipped_ids)


def get_analysis_run(database_path: Path, run_id: str) -> AnalysisRun:
    """Load one durable provider run."""

    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, app_id, provider, model, state, review_revision_ids_json, "
            "metric_policy_json, cancel_requested, error_code, report_version_id, "
            "input_tokens, cached_input_tokens, output_tokens, "
            "early_review_revision_ids_json, recent_review_revision_ids_json, "
            "report_kind, oversized_review_count, operation, base_report_id, "
            "refresh_job_id, "
            "CASE WHEN report_kind = 'main' THEN COALESCE(("
            "SELECT SUM(CASE WHEN json_valid(batch.result_json) THEN "
            "json_array_length(json_extract(batch.result_json, "
            "'$.completed_review_revision_ids')) ELSE 0 END) "
            "FROM analysis_theme_batches batch "
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
        operation=row[17],
        base_report_id=row[18],
        refresh_job_id=row[19],
        extracted_review_count=int(row[20]),
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
        connection.execute(
            "UPDATE analysis_jobs SET "
            "state = CASE WHEN state = 'queued' THEN 'cancelled' ELSE state END, "
            "cancel_requested = CASE WHEN state = 'running' THEN 1 ELSE cancel_requested END, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ("
            "SELECT refresh_job_id FROM analysis_runs WHERE id = ?) "
            "AND state IN ('queued', 'running')",
            (run_id,),
        )
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


def fail_analysis_run(database_path: Path, run_id: str, error_code: str) -> None:
    """Move accepted queued or running work to a safe failed state."""

    with connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_runs SET state = 'failed', error_code = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ? "
            "AND state IN ('queued', 'running')",
            (error_code, run_id),
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
        connection.execute(
            "UPDATE analysis_jobs SET state = 'queued', cancel_requested = 0, "
            "error_code = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ("
            "SELECT refresh_job_id FROM analysis_runs WHERE id = ?) "
            "AND state IN ('failed', 'cancelled')",
            (run_id,),
        )
        cursor = connection.execute(
            "UPDATE analysis_runs SET state = 'queued', cancel_requested = 0, "
            "error_code = NULL, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND state IN ('failed', 'cancelled')",
            (run_id,),
        )
    if cursor.rowcount == 0:
        raise ValueError("Only failed or cancelled analysis can be retried")
    return get_analysis_run(database_path, run_id)
