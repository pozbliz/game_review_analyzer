"""Immutable Report Version persistence tests."""

from pathlib import Path
import sqlite3

import pytest

from game_review_analyzer.domain.analysis import AnalysisResult
from game_review_analyzer.domain.reports import (
    ReportVersion,
    ThemeMetricPolicy,
    ThemeMetrics,
)
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import (
    load_report_version,
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
        schema_version="1.0",
        report_version_id="report-1",
        app_id=1145350,
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
