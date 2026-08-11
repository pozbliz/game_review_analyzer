"""Append-only SQLite persistence for immutable Report Version snapshots."""

from pathlib import Path
import sqlite3

from game_review_analyzer.domain.reports import ReportVersion


def save_report_version(database_path: Path, report: ReportVersion) -> None:
    """Append one Report Version bound to revisions owned by its game."""

    placeholders: str = ",".join("?" for _ in report.review_revision_ids)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        owned_revision_rows: set[tuple[int, str]] = {
            (row[0], row[1])
            for row in connection.execute(
                "SELECT review_revisions.id, reviews.id FROM review_revisions "
                "JOIN reviews ON reviews.id = review_revisions.review_id "
                f"WHERE reviews.app_id = ? AND review_revisions.id IN ({placeholders})",
                (report.app_id, *report.review_revision_ids),
            )
        }
        owned_revision_ids: set[int] = {row[0] for row in owned_revision_rows}
        if owned_revision_ids != set(report.review_revision_ids):
            raise ValueError("Report revisions must exist and belong to exactly one game")
        completed_review_ids: tuple[str, ...] = (
            report.analysis_result.completed_review_revision_ids
        )
        if (
            {row[1] for row in owned_revision_rows} != set(completed_review_ids)
            or len(completed_review_ids) != len(owned_revision_rows)
        ):
            raise ValueError("Report analysis scope must match its exact Review Revisions")
        connection.execute(
            "INSERT INTO report_versions(id, app_id, snapshot_json) VALUES (?, ?, ?)",
            (report.report_version_id, report.app_id, report.model_dump_json()),
        )
        connection.executemany(
            "INSERT INTO report_version_review_revisions("
            "report_version_id, review_revision_id) VALUES (?, ?)",
            (
                (report.report_version_id, revision_id)
                for revision_id in report.review_revision_ids
            ),
        )


def load_report_version(
    database_path: Path, report_version_id: str
) -> ReportVersion | None:
    """Load one immutable Report Version snapshot when it exists."""

    with sqlite3.connect(database_path) as connection:
        row: tuple[str] | None = connection.execute(
            "SELECT snapshot_json FROM report_versions WHERE id = ?",
            (report_version_id,),
        ).fetchone()
        if row is None:
            return None
        report: ReportVersion = ReportVersion.model_validate_json(row[0])
        bound_revision_ids: set[int] = {
            binding[0]
            for binding in connection.execute(
                "SELECT review_revision_id FROM report_version_review_revisions "
                "WHERE report_version_id = ?",
                (report_version_id,),
            )
        }
    if bound_revision_ids != set(report.review_revision_ids):
        raise ValueError("Stored Report Version scope bindings are inconsistent")
    return report
