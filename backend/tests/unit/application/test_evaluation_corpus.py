"""Selection tests for the human-reviewed evaluation subset."""

from game_review_analyzer.application.evaluation_corpus import select_balanced_reviews
from game_review_analyzer.domain.reviews import SteamReview


def test_selection_caps_each_recommendation_group_and_preserves_source_order() -> None:
    reviews = tuple(
        review(str(index), recommended)
        for index, recommended in enumerate((True, True, True, False, False, False), start=1)
    )

    selected = select_balanced_reviews(reviews, per_recommendation=2)

    assert [item.review_id for item in selected] == ["1", "2", "4", "5"]


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
