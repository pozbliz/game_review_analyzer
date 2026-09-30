"""Main Report selection and batching rules."""

from game_review_analyzer.application.main_report import pack_review_batches
from game_review_analyzer.domain.reviews import SteamReview


def test_batches_respect_character_capacity_and_250_review_ceiling() -> None:
    reviews: dict[int, SteamReview] = {
        revision_id: review(revision_id, "text")
        for revision_id in range(1, 252)
    }

    assert tuple(pack_review_batches(tuple(reviews), reviews, 10_000)) == (
        tuple(range(1, 251)),
        (251,),
    )
    assert tuple(pack_review_batches((1, 2, 3), reviews, 8)) == (
        (1, 2),
        (3,),
    )


def review(position: int, text: str) -> SteamReview:
    return SteamReview(
        review_id=f"review-{position}",
        language="english",
        text=text,
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
