"""Report summary and complete-evidence HTTP contract tests."""

from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from game_review_analyzer.application.theme_metrics import calculate_theme_metrics
from game_review_analyzer.domain.analysis import AnalysisResult, OpinionPoint, Theme
from game_review_analyzer.domain.reports import ReportVersion, ThemeMetricPolicy
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import save_report_version
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    save_review_revisions,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings


def test_report_summary_and_complete_evidence_preserve_metrics_and_context(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)

    with TestClient(create_app(Settings(database_path=database_path))) as client:
        report_response = client.get("/api/reports/report-1")
        evidence_response = client.get(
            "/api/reports/report-1/themes/responsive-combat/evidence"
        )

    assert report_response.status_code == 200
    report = report_response.json()
    assert report["game"] == {"app_id": 1145350, "title": "Hades II"}
    assert report["scope"] == {"review_count": 2, "thresholds_calibrated": False}
    assert report["provenance"] == {
        "provider": "manual-codex",
        "model": "fixture-model",
        "request_id": "request-1",
        "scope_sha256": "a" * 64,
    }
    theme = report["positive_themes"][0]
    assert theme["title"] == "Responsive combat"
    assert theme["support"] == {"count": 2, "percentage": 100.0, "denominator": 2}
    assert theme["evidence_count"] == 2
    assert theme["primary_category"] == "Gameplay and mechanics"
    assert [item["excerpt"] for item in theme["representative_evidence"]] == [
        "Combat is responsive",
        "Fights feel responsive",
    ]

    assert evidence_response.status_code == 200
    evidence = evidence_response.json()
    assert evidence["theme_id"] == "responsive-combat"
    assert len(evidence["items"]) == 2
    assert evidence["items"][0]["review"]["text"] == "Combat is responsive."
    assert evidence["items"][0]["review"]["recommended"] is True
    assert evidence["items"][0]["review"]["playtime_at_review_minutes"] == 120
    assert evidence["items"][0]["review"]["votes_helpful"] == 3


def seed_report(database_path: Path) -> None:
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
            review_count=2,
            source_status="partial",
            missing_fields=frozenset(
                {"capsule_image_url", "release_date", "release_status"}
            ),
        ),
    )
    reviews: tuple[SteamReview, ...] = (
        review("review-1", "Combat is responsive.", True, 120, 3),
        review("review-2", "Fights feel responsive.", False, 240, 5),
    )
    save_review_revisions(database_path, 1145350, reviews)
    with sqlite3.connect(database_path) as connection:
        revision_ids: tuple[int, ...] = tuple(
            row[0]
            for row in connection.execute(
                "SELECT id FROM review_revisions ORDER BY id"
            ).fetchall()
        )
    points: tuple[OpinionPoint, ...] = (
        OpinionPoint(
            id="point-1",
            review_revision_id="review-1",
            excerpt="Combat is responsive",
            sentiment="positive",
            subject="combat responsiveness",
            supports_theme_id="responsive-combat",
        ),
        OpinionPoint(
            id="point-2",
            review_revision_id="review-2",
            excerpt="Fights feel responsive",
            sentiment="positive",
            subject="combat responsiveness",
            supports_theme_id="responsive-combat",
        ),
    )
    themes: tuple[Theme, ...] = (
        Theme(
            id="responsive-combat",
            title="Responsive combat",
            summary="Players describe combat as immediately responsive.",
            polarity="positive",
            primary_category="Gameplay and mechanics",
            related_categories=("Controls, interface, and onboarding",),
            opinion_point_ids=("point-1", "point-2"),
            technical=False,
            opposes_theme_id=None,
        ),
    )
    policy = ThemeMetricPolicy(
        minimum_support_count=2,
        minimum_support_percentage=1,
        technical_minimum_support_count=2,
        technical_minimum_support_percentage=1,
    )
    analysis = AnalysisResult(
        schema_version="1.0",
        request_id="request-1",
        scope_sha256="a" * 64,
        provider="manual-codex",
        model="fixture-model",
        completed_review_revision_ids=("review-1", "review-2"),
        opinion_points=points,
        themes=themes,
        mechanic_classifications=(),
    )
    save_report_version(
        database_path,
        ReportVersion(
            schema_version="1.0",
            report_version_id="report-1",
            app_id=1145350,
            review_revision_ids=revision_ids,
            analysis_result=analysis,
            metric_policy=policy,
            theme_metrics=calculate_theme_metrics(
                analysis.completed_review_revision_ids, points, themes, policy
            ),
            thresholds_calibrated=False,
        ),
    )


def review(
    review_id: str,
    text: str,
    recommended: bool,
    playtime_at_review_minutes: int,
    votes_helpful: int,
) -> SteamReview:
    return SteamReview(
        review_id=review_id,
        language="english",
        text=text,
        source_created_at=100,
        source_updated_at=100,
        recommended=recommended,
        votes_helpful=votes_helpful,
        votes_funny=0,
        weighted_vote_score=0,
        steam_purchase=True,
        received_for_free=False,
        written_during_early_access=False,
        playtime_forever_minutes=playtime_at_review_minutes + 60,
        playtime_at_review_minutes=playtime_at_review_minutes,
    )
