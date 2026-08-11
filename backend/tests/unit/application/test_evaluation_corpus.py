"""Selection tests for the human-reviewed evaluation subset."""

from game_review_analyzer.application.evaluation_corpus import (
    partition_reviews_for_evaluation,
    select_balanced_reviews,
    select_latest_reviews,
)
from game_review_analyzer.domain.reviews import SteamReview


def test_selection_caps_each_recommendation_group_and_preserves_source_order() -> None:
    reviews = tuple(
        review(str(index), recommended)
        for index, recommended in enumerate((True, True, True, False, False, False), start=1)
    )

    selected = select_balanced_reviews(reviews, per_recommendation=2)

    assert [item.review_id for item in selected] == ["1", "2", "4", "5"]


def test_latest_selection_preserves_natural_recommendation_distribution() -> None:
    reviews = tuple(
        review(str(index), recommended)
        for index, recommended in enumerate((True, True, False, True), start=1)
    )

    selected = select_latest_reviews(reviews, limit=3)

    assert [item.review_id for item in selected] == ["1", "2", "3"]


def test_stability_partitions_are_deterministic_and_preserve_every_review() -> None:
    reviews = tuple(review(str(index), True) for index in range(1, 7))

    contiguous = partition_reviews_for_evaluation(reviews, "contiguous", batch_size=2)
    interleaved = partition_reviews_for_evaluation(reviews, "interleaved", batch_size=2)
    hashed = partition_reviews_for_evaluation(reviews, "hashed", batch_size=2)

    assert [[item.review_id for item in batch] for batch in contiguous] == [
        ["1", "2"],
        ["3", "4"],
        ["5", "6"],
    ]
    assert [[item.review_id for item in batch] for batch in interleaved] == [
        ["1", "4"],
        ["2", "5"],
        ["3", "6"],
    ]
    expected_ids: set[str] = {review.review_id for review in reviews}
    for batches in (contiguous, interleaved, hashed):
        actual_ids: list[str] = [item.review_id for batch in batches for item in batch]
        assert set(actual_ids) == expected_ids
        assert len(actual_ids) == len(expected_ids)
    assert hashed == partition_reviews_for_evaluation(
        reviews, "hashed", batch_size=2
    )


def review(review_id: str, recommended: bool) -> SteamReview:
    return SteamReview(
        review_id=review_id,
        language="english",
        text=f"Review {review_id}",
        source_created_at=100,
        source_updated_at=100,
        recommended=recommended,
        votes_helpful=0,
        votes_funny=0,
        weighted_vote_score=0,
        steam_purchase=True,
        received_for_free=False,
        written_during_early_access=False,
        playtime_forever_minutes=10,
        playtime_at_review_minutes=10,
    )
