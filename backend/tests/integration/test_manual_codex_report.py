"""Fixture-driven Manual Codex to immutable report integration test."""

import json
from pathlib import Path
import sqlite3
from typing import Any

from game_review_analyzer.application.manual_codex import build_analysis_request
from game_review_analyzer.application.report_creation import create_manual_codex_report
from game_review_analyzer.domain.analysis import AnalysisSourceReview
from game_review_analyzer.domain.reports import ReportVersion, ThemeMetricPolicy
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import load_report_version
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    save_review_revisions,
)


def test_validated_fixture_creates_a_provisional_immutable_report(tmp_path: Path) -> None:
    fixture_path: Path = (
        Path(__file__).parents[1]
        / "fixtures"
        / "analysis_evaluation"
        / "synthetic_v1.json"
    )
    game: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))[
        "games"
    ][0]
    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(database_path, metadata(game))
    steam_reviews: tuple[SteamReview, ...] = tuple(
        steam_review(review) for review in game["reviews"]
    )
    save_review_revisions(database_path, game["app_id"], steam_reviews)
    with sqlite3.connect(database_path) as connection:
        revision_ids: tuple[int, ...] = tuple(
            row[0]
            for row in connection.execute(
                "SELECT id FROM review_revisions ORDER BY id"
            ).fetchall()
        )
    request = build_analysis_request(
        request_id="fixture-request",
        app_id=game["app_id"],
        game_title=game["title"],
        reviews=(
            AnalysisSourceReview(
                review_revision_id=review["review_revision_id"], text=review["text"]
            )
            for review in game["reviews"]
        ),
    )
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "request_id": request.request_id,
        "scope_sha256": request.scope_sha256,
        "provider": "manual-codex",
        "model": "synthetic-fixture",
        "completed_review_revision_ids": [
            review["review_revision_id"] for review in game["reviews"]
        ],
        "opinion_points": game["opinion_points"],
        "themes": game["themes"],
        "mechanic_classifications": game["mechanic_classifications"],
    }

    report: ReportVersion = create_manual_codex_report(
        database_path=database_path,
        report_version_id="report-fixture-1",
        request=request,
        result_json=json.dumps(result),
        review_revision_ids=revision_ids,
        metric_policy=ThemeMetricPolicy(
            minimum_support_count=2,
            minimum_support_percentage=0,
            technical_minimum_support_count=2,
            technical_minimum_support_percentage=0,
        ),
    )

    assert report.thresholds_calibrated is False
    assert [item.theme_id for item in report.theme_metrics.positive_headlines] == [
        "ev-t1"
    ]
    assert [item.theme_id for item in report.theme_metrics.negative_headlines] == [
        "ev-t2"
    ]
    assert load_report_version(database_path, report.report_version_id) == report


def metadata(game: dict[str, Any]) -> SteamMetadata:
    return SteamMetadata(
        app_id=game["app_id"],
        title=game["title"],
        developers=(),
        capsule_image_url=None,
        release_date=None,
        release_status="unknown",
        review_count=len(game["reviews"]),
        source_status="partial",
        missing_fields=frozenset(
            {"capsule_image_url", "release_date", "release_status"}
        ),
    )


def steam_review(review: dict[str, Any]) -> SteamReview:
    return SteamReview(
        review_id=review["review_revision_id"],
        language="english",
        text=review["text"],
        source_created_at=100,
        source_updated_at=100,
        recommended=review["recommended"],
        votes_helpful=0,
        votes_funny=0,
        weighted_vote_score=0,
        steam_purchase=True,
        received_for_free=False,
        written_during_early_access=False,
        playtime_forever_minutes=60,
        playtime_at_review_minutes=60,
    )
