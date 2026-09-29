"""Immutable Report Version persistence tests."""

import json
from pathlib import Path
import sqlite3

import pytest

from game_review_analyzer.domain.analysis import AnalysisResult
from game_review_analyzer.domain.reports import (
    AggregateReport,
    AggregateThemeMetrics,
    ReportVersion,
    ThemeMetricPolicy,
    ThemeMetrics,
)
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import (
    load_aggregate_report_slot,
    load_report_version,
    save_aggregate_report,
    save_report_version,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    save_review_revisions,
)


def test_report_version_round_trips_and_cannot_be_overwritten(tmp_path: Path) -> None:
    database_path: Path = initialized_dataset(tmp_path)
    with sqlite3.connect(database_path) as connection:
        revision_ids: tuple[int, ...] = tuple(
            row[0]
            for row in connection.execute(
                "SELECT id FROM review_revisions ORDER BY id"
            ).fetchall()
        )
    report: ReportVersion = report_version(revision_ids)

    save_report_version(database_path, report)

    assert load_report_version(database_path, report.report_version_id) == report
    with pytest.raises(sqlite3.IntegrityError):
        save_report_version(
            database_path,
            report.model_copy(update={"thresholds_calibrated": True}),
        )
    assert load_report_version(database_path, report.report_version_id) == report

    mismatched_analysis: AnalysisResult = report.analysis_result.model_copy(
        update={"completed_review_revision_ids": ("wrong-review", "review-2")}
    )
    with pytest.raises(ValueError, match="analysis scope"):
        save_report_version(
            database_path,
            report.model_copy(
                update={
                    "report_version_id": "report-2",
                    "analysis_result": mismatched_analysis,
                }
            ),
        )


def test_report_version_rejects_revisions_outside_its_game(tmp_path: Path) -> None:
    database_path: Path = initialized_dataset(tmp_path)

    with pytest.raises(ValueError, match="exactly one game"):
        save_report_version(database_path, report_version((999,)))


def test_migration_upgrades_existing_report_to_typed_metadata_snapshot(
    tmp_path: Path,
) -> None:
    database_path: Path = initialized_dataset(tmp_path)
    with sqlite3.connect(database_path) as connection:
        revision_ids: tuple[int, ...] = tuple(
            row[0] for row in connection.execute("SELECT id FROM review_revisions")
        )
    save_report_version(database_path, report_version(revision_ids))
    with sqlite3.connect(database_path) as connection:
        snapshot: dict[str, object] = json.loads(
            connection.execute(
                "SELECT snapshot_json FROM report_versions WHERE id = 'report-1'"
            ).fetchone()[0]
        )
        snapshot.pop("metadata_snapshot")
        snapshot["schema_version"] = "1.0"
        connection.execute(
            "UPDATE report_versions SET snapshot_json = ? WHERE id = 'report-1'",
            (json.dumps(snapshot),),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = 5")

    initialize_database(database_path)

    migrated: ReportVersion | None = load_report_version(database_path, "report-1")
    assert migrated is not None
    assert migrated.schema_version == "2.0"
    assert migrated.metadata_snapshot.title == "Hades II"


def test_aggregate_report_slots_replace_independently(tmp_path: Path) -> None:
    database_path: Path = initialized_dataset(tmp_path)
    with sqlite3.connect(database_path) as connection:
        revision_ids: tuple[int, ...] = tuple(
            row[0] for row in connection.execute(
                "SELECT id FROM review_revisions ORDER BY id"
            )
        )
    main_report: AggregateReport = aggregate_report(
        "main-report", "main", revision_ids
    )
    first_test_report: AggregateReport = aggregate_report(
        "test-report-1", "test", revision_ids
    )
    second_test_report: AggregateReport = aggregate_report(
        "test-report-2", "test", revision_ids
    )

    save_aggregate_report(database_path, main_report)
    save_aggregate_report(database_path, first_test_report)
    save_aggregate_report(database_path, second_test_report)

    assert load_aggregate_report_slot(database_path, 1145350, "main") == main_report
    assert (
        load_aggregate_report_slot(database_path, 1145350, "test")
        == second_test_report
    )
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM report_versions WHERE app_id = ?",
            (1145350,),
        ).fetchone()[0] == 2


def initialized_dataset(tmp_path: Path) -> Path:
    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(
        database_path,
        SteamMetadata(
            app_id=1145350,
            title="Hades II",
            developers=("Supergiant Games",),
            capsule_image_url=None,
            release_date=None,
            release_status="unknown",
            review_count=None,
            source_status="partial",
            missing_fields=frozenset(
                {"capsule_image_url", "release_date", "release_status", "review_count"}
            ),
        ),
    )
    reviews: tuple[SteamReview, ...] = tuple(
        SteamReview(
            review_id=f"review-{index}",
            language="english",
            text=text,
            source_created_at=100,
            source_updated_at=100,
            recommended=True,
            votes_helpful=0,
            votes_funny=0,
            weighted_vote_score=0,
            steam_purchase=True,
            received_for_free=False,
            written_during_early_access=False,
            playtime_forever_minutes=60,
            playtime_at_review_minutes=60,
        )
        for index, text in enumerate(("Great combat.", "Great movement."), start=1)
    )
    save_review_revisions(database_path, 1145350, reviews)
    return database_path


def report_version(revision_ids: tuple[int, ...]) -> ReportVersion:
    return ReportVersion(
        schema_version="2.0",
        report_version_id="report-1",
        app_id=1145350,
        metadata_snapshot=SteamMetadata(
            app_id=1145350,
            title="Hades II",
            developers=("Supergiant Games",),
            capsule_image_url=None,
            release_date=None,
            release_status="unknown",
            review_count=None,
            source_status="partial",
            missing_fields=frozenset(
                {"capsule_image_url", "release_date", "release_status", "review_count"}
            ),
        ),
        review_revision_ids=revision_ids,
        analysis_result=AnalysisResult(
            schema_version="1.0",
            request_id="request-1",
            scope_sha256="a" * 64,
            provider="manual-codex",
            model="gpt-5.6-luna",
            completed_review_revision_ids=("review-1", "review-2"),
            opinion_points=(),
            themes=(),
            mechanic_classifications=(),
        ),
        metric_policy=ThemeMetricPolicy(
            minimum_support_count=2,
            minimum_support_percentage=1,
            technical_minimum_support_count=3,
            technical_minimum_support_percentage=2,
        ),
        theme_metrics=ThemeMetrics(
            all_themes=(),
            positive_headlines=(),
            negative_headlines=(),
            technical_themes=(),
            mixed_reception=(),
        ),
        thresholds_calibrated=False,
    )


def aggregate_report(
    report_id: str,
    kind: str,
    revision_ids: tuple[int, ...],
) -> AggregateReport:
    return AggregateReport(
        schema_version="3.0",
        report_id=report_id,
        kind=kind,
        app_id=1145350,
        metadata_snapshot=SteamMetadata(
            app_id=1145350,
            title="Hades II",
            developers=("Supergiant Games",),
            capsule_image_url=None,
            release_date=None,
            release_status="unknown",
            review_count=None,
            source_status="partial",
            missing_fields=frozenset(
                {"capsule_image_url", "release_date", "release_status", "review_count"}
            ),
        ),
        review_revision_ids=revision_ids,
        oldest_review_revision_ids=(revision_ids[0],),
        newest_review_revision_ids=(revision_ids[1],),
        provider="codex-cli",
        model="gpt-5.6-luna",
        contract_version="3.0",
        themes=(),
        memberships=(),
        theme_metrics=AggregateThemeMetrics(
            all_themes=(),
            positive_headlines=(),
            negative_headlines=(),
        ),
    )
