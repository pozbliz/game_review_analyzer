"""Version 3 aggregate report persistence tests."""

from pathlib import Path
import sqlite3

import pytest

from game_review_analyzer.domain.reports import AggregateReport
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.report_versions import (
    load_aggregate_report_slot,
    save_aggregate_report,
)
from tests.integration.aggregate_report_seed import seed_aggregate_report


def test_aggregate_report_slots_replace_independently(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_aggregate_report(database_path)
    main_report: AggregateReport | None = load_aggregate_report_slot(
        database_path, 1145350, "main"
    )
    assert main_report is not None
    first_test: AggregateReport = main_report.model_copy(
        update={"report_id": "test-1", "kind": "test"}
    )
    second_test: AggregateReport = first_test.model_copy(
        update={"report_id": "test-2"}
    )

    save_aggregate_report(database_path, first_test)
    save_aggregate_report(database_path, second_test)

    assert load_aggregate_report_slot(database_path, 1145350, "main") == main_report
    assert load_aggregate_report_slot(database_path, 1145350, "test") == second_test
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM report_versions WHERE app_id = ?", (1145350,)
        ).fetchone()[0] == 2


def test_aggregate_report_rejects_revisions_outside_its_game(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_aggregate_report(database_path)
    report: AggregateReport | None = load_aggregate_report_slot(
        database_path, 1145350, "main"
    )
    assert report is not None
    invalid: AggregateReport = report.model_copy(
        update={
            "report_id": "invalid",
            "review_revision_ids": (999,),
            "oldest_review_revision_ids": (999,),
            "newest_review_revision_ids": (),
        }
    )

    with pytest.raises(ValueError, match="must exist and belong"):
        save_aggregate_report(database_path, invalid)


def test_version_3_migration_removes_legacy_reports_runs_and_extractions(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_aggregate_report(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM schema_migrations WHERE version = 18")
        connection.execute(
            "CREATE TABLE review_opinion_extractions (review_revision_id INTEGER)"
        )
        connection.execute(
            "INSERT INTO report_versions(id, app_id, snapshot_json) "
            "VALUES ('legacy-report', 1145350, '{}')"
        )
        connection.execute(
            "INSERT INTO analysis_runs("
            "id, app_id, provider, model, state, review_revision_ids_json, "
            "metric_policy_json, report_version_id) VALUES "
            "('legacy-run', 1145350, 'ollama', 'old-model', 'completed', "
            "'[]', '{}', 'legacy-report')"
        )

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM report_versions WHERE report_kind IS NULL"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM analysis_runs WHERE report_kind IS NULL"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name = 'review_opinion_extractions'"
        ).fetchone()[0] == 0
