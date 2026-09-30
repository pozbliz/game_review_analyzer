"""First Main Report integration tests."""

from pathlib import Path

from game_review_analyzer.domain.reports import ThemeMetricPolicy
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.analysis_runs import (
    create_analysis_run,
)
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.jobs import (
    create_full_job,
    finish_job,
    start_job,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
    save_review_revisions,
)


def test_main_report_selects_500_oldest_and_500_newest_complete_reviews(
    tmp_path: Path,
) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=1_002, oversized=1)

    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        cohort_size=500,
        report_kind="main",
    )

    reviews: dict[int, SteamReview] = load_review_revisions_by_ids(
        database_path, run.review_revision_ids
    )
    oldest_times: list[int] = [
        reviews[revision_id].source_created_at
        for revision_id in run.early_review_revision_ids
    ]
    newest_times: list[int] = [
        reviews[revision_id].source_created_at
        for revision_id in run.recent_review_revision_ids
    ]
    assert len(run.early_review_revision_ids) == 500
    assert len(run.recent_review_revision_ids) == 500
    assert set(run.early_review_revision_ids).isdisjoint(run.recent_review_revision_ids)
    assert oldest_times == list(range(2, 502))
    assert newest_times == list(range(503, 1_003))
    assert reviews[run.early_review_revision_ids[0]].text == "Review 2"


def seeded_database(
    tmp_path: Path,
    *,
    review_count: int,
    oversized: int | None = None,
) -> Path:
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
            review_count=review_count,
            source_status="partial",
            missing_fields=frozenset(
                {"capsule_image_url", "release_date", "release_status"}
            ),
        ),
    )
    reviews: tuple[SteamReview, ...] = tuple(
        SteamReview(
            review_id=f"review-{position:04d}",
            language="english",
            text="x" * 32_001 if position == oversized else f"Review {position}",
            source_created_at=position,
            source_updated_at=position,
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
        for position in range(1, review_count + 1)
    )
    save_review_revisions(database_path, 1145350, reviews)
    job = create_full_job(database_path, 1145350)
    start_job(database_path, job.id)
    finish_job(database_path, job.id, "completed")
    return database_path


def metric_policy() -> ThemeMetricPolicy:
    return ThemeMetricPolicy(
        minimum_support_count=1,
        minimum_support_percentage=5,
        technical_minimum_support_count=1,
        technical_minimum_support_percentage=5,
        maximum_headlines_per_polarity=5,
    )
