"""Shared Version 3 aggregate-report fixture."""

from pathlib import Path
import sqlite3

from game_review_analyzer.domain.reports import (
    AggregateReport,
    AggregateThemeMetrics,
    ThemeMetricPolicy,
)
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import save_aggregate_report
from game_review_analyzer.infrastructure.persistence.review_revisions import save_review_revisions


def seed_aggregate_report(database_path: Path) -> None:
    initialize_database(database_path)
    metadata = SteamMetadata(
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
    )
    save_game_dataset(database_path, metadata)
    save_review_revisions(
        database_path,
        metadata.app_id,
        (
            review("review-1", "Combat is responsive.", True),
            review("review-2", "Fights feel responsive.", False),
        ),
    )
    with sqlite3.connect(database_path) as connection:
        revision_ids = tuple(
            int(row[0])
            for row in connection.execute(
                "SELECT id FROM review_revisions ORDER BY id"
            )
        )
    save_aggregate_report(
        database_path,
        AggregateReport(
            schema_version="3.0",
            report_id="report-1",
            kind="main",
            app_id=metadata.app_id,
            metadata_snapshot=metadata,
            review_revision_ids=revision_ids,
            oldest_review_revision_ids=(revision_ids[0],),
            newest_review_revision_ids=(revision_ids[1],),
            provider="codex-cli",
            model="gpt-5.6-luna",
            contract_version="3.1",
            metric_policy=ThemeMetricPolicy(
                minimum_support_count=1,
                minimum_support_percentage=5,
                technical_minimum_support_count=1,
                technical_minimum_support_percentage=5,
            ),
            themes=(),
            memberships=(),
            theme_metrics=AggregateThemeMetrics(
                all_themes=(),
                positive_headlines=(),
                negative_headlines=(),
            ),
        ),
    )


def review(review_id: str, text: str, recommended: bool) -> SteamReview:
    return SteamReview(
        review_id=review_id,
        language="english",
        text=text,
        source_created_at=100,
        source_updated_at=100,
        recommended=recommended,
        votes_helpful=3,
        votes_funny=0,
        weighted_vote_score=0,
        steam_purchase=True,
        received_for_free=False,
        written_during_early_access=False,
        playtime_forever_minutes=180,
        playtime_at_review_minutes=120,
        author_steamid=None,
        author_name=None,
        author_avatar_url=None,
    )
