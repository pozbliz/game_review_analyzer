"""Append-only SQLite persistence for immutable Report Version snapshots."""

from pathlib import Path
import sqlite3

from game_review_analyzer.domain.reports import AggregateReport


def save_aggregate_report(database_path: Path, report: AggregateReport) -> None:
    """Atomically replace one Version 3 report slot and its exact bindings."""

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _save_aggregate_report(connection, report)


def complete_aggregate_report_run(
    database_path: Path,
    run_id: str,
    report: AggregateReport,
    *,
    input_tokens: int | None,
    cached_input_tokens: int | None,
    output_tokens: int | None,
) -> bool:
    """Replace one report slot and complete its uncancelled run atomically."""

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        run_row = connection.execute(
            "SELECT state, cancel_requested, operation, base_report_id "
            "FROM analysis_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if run_row is None or run_row[0] != "running":
            raise ValueError("Analysis run is not running")
        if run_row[1]:
            connection.execute(
                "UPDATE analysis_runs SET state = 'cancelled', "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (run_id,),
            )
            return False
        current_row = connection.execute(
            "SELECT id FROM report_versions WHERE app_id = ? AND report_kind = ?",
            (report.app_id, report.kind),
        ).fetchone()
        current_report_id: str | None = current_row[0] if current_row else None
        if run_row[2] in ("extend", "replace"):
            if current_report_id != run_row[3]:
                raise ValueError("Base report changed during analysis")
        elif run_row[2] == "create" and current_report_id is not None:
            raise ValueError("Report slot changed during analysis")
        _save_aggregate_report(connection, report)
        connection.execute(
            "UPDATE analysis_runs SET state = 'completed', report_version_id = ?, "
            "input_tokens = ?, cached_input_tokens = ?, output_tokens = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (
                report.report_id,
                input_tokens,
                cached_input_tokens,
                output_tokens,
                run_id,
            ),
        )
    return True


def _save_aggregate_report(
    connection: sqlite3.Connection,
    report: AggregateReport,
) -> None:
    placeholders: str = ",".join("?" for _ in report.review_revision_ids)
    owned_revision_ids: set[int] = {
        int(row[0])
        for row in connection.execute(
            "SELECT review_revisions.id FROM review_revisions "
            "JOIN reviews ON reviews.id = review_revisions.review_id "
            f"WHERE reviews.app_id = ? AND review_revisions.id IN ({placeholders})",
            (report.app_id, *report.review_revision_ids),
        )
    }
    if owned_revision_ids != set(report.review_revision_ids):
        raise ValueError("Report revisions must exist and belong to exactly one game")
    connection.execute(
        "UPDATE analysis_runs SET report_version_id = NULL "
        "WHERE report_version_id IN ("
        "SELECT id FROM report_versions WHERE app_id = ? AND report_kind = ?) ",
        (report.app_id, report.kind),
    )
    connection.execute(
        "DELETE FROM report_versions WHERE app_id = ? AND report_kind = ?",
        (report.app_id, report.kind),
    )
    connection.execute(
        "INSERT INTO report_versions(id, app_id, snapshot_json, report_kind) "
        "VALUES (?, ?, ?, ?)",
        (report.report_id, report.app_id, report.model_dump_json(), report.kind),
    )
    connection.executemany(
        "INSERT INTO report_version_review_revisions("
        "report_version_id, review_revision_id) VALUES (?, ?)",
        (
            (report.report_id, revision_id)
            for revision_id in report.review_revision_ids
        ),
    )


def load_aggregate_report_slot(
    database_path: Path,
    app_id: int,
    kind: str,
) -> AggregateReport | None:
    """Load the current Version 3 report from one game slot."""

    with sqlite3.connect(database_path) as connection:
        row: tuple[str] | None = connection.execute(
            "SELECT snapshot_json FROM report_versions "
            "WHERE app_id = ? AND report_kind = ?",
            (app_id, kind),
        ).fetchone()
    return AggregateReport.model_validate_json(row[0]) if row else None


def load_aggregate_report_created_at(
    database_path: Path,
    app_id: int,
    kind: str,
) -> str | None:
    """Load the creation timestamp for one Version 3 report slot."""

    with sqlite3.connect(database_path) as connection:
        row: tuple[str] | None = connection.execute(
            "SELECT created_at FROM report_versions "
            "WHERE app_id = ? AND report_kind = ?",
            (app_id, kind),
        ).fetchone()
    return str(row[0]) if row else None
