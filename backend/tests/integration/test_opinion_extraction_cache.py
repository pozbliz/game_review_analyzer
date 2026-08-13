"""Durable validated Opinion Point extraction cache tests."""

from pathlib import Path
import sqlite3

from game_review_analyzer.domain.analysis import (
    ExtractedOpinionPoint,
    OpinionExtractionResult,
    OpinionSentiment,
)
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.opinion_extractions import (
    load_opinion_extractions,
    save_opinion_extraction_batch,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    save_review_revisions,
)


def test_validated_batch_caches_reviews_with_and_without_opinions(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(database_path, metadata())
    save_review_revisions(
        database_path,
        1145350,
        (review("review-1", "Combat feels responsive."), review("review-2", "Fine.")),
    )
    revision_ids_by_review_id: dict[str, int] = latest_revision_ids(database_path)
    result = OpinionExtractionResult(
        schema_version="1.0",
        request_id="batch-1",
        scope_sha256="a" * 64,
        provider="codex-cli",
        model="gpt-5.6-luna",
        completed_review_revision_ids=("review-1", "review-2"),
        opinion_points=(
            ExtractedOpinionPoint(
                id="provider-point-1",
                review_revision_id="review-1",
                excerpt="Combat feels responsive.",
                sentiment=OpinionSentiment.POSITIVE,
                subject="combat responsiveness",
            ),
        ),
    )

    save_opinion_extraction_batch(
        database_path,
        revision_ids_by_review_id=revision_ids_by_review_id,
        result=result,
        contract_version="1.0",
    )

    cached = load_opinion_extractions(
        database_path,
        revision_ids=tuple(revision_ids_by_review_id.values()),
        provider="codex-cli",
        model="gpt-5.6-luna",
        contract_version="1.0",
    )
    assert set(cached) == set(revision_ids_by_review_id.values())
    assert cached[revision_ids_by_review_id["review-2"]] == ()
    first_points = cached[revision_ids_by_review_id["review-1"]]
    assert first_points[0].id == (
        f"revision-{revision_ids_by_review_id['review-1']}-opinion-1"
    )


def latest_revision_ids(database_path: Path) -> dict[str, int]:
    with sqlite3.connect(database_path) as connection:
        return {
            str(review_id): int(revision_id)
            for revision_id, review_id in connection.execute(
                "SELECT review_revisions.id, reviews.id FROM review_revisions "
                "JOIN reviews ON reviews.id = review_revisions.review_id"
            )
        }


def metadata() -> SteamMetadata:
    return SteamMetadata(
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


def review(review_id: str, text: str) -> SteamReview:
    return SteamReview(
        review_id=review_id,
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
        playtime_forever_minutes=10,
        playtime_at_review_minutes=10,
    )
