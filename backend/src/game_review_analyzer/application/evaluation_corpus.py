"""Selection rules for a small human-reviewed analysis evaluation subset."""

from collections.abc import Iterable
from itertools import islice

from game_review_analyzer.domain.reviews import SteamReview


def select_latest_reviews(
    reviews: Iterable[SteamReview],
    limit: int,
) -> tuple[SteamReview, ...]:
    """Keep the latest source-ordered reviews without balancing recommendations."""

    if limit <= 0:
        raise ValueError("limit must be positive")
    return tuple(islice(reviews, limit))


def select_balanced_reviews(
    reviews: Iterable[SteamReview],
    per_recommendation: int,
) -> tuple[SteamReview, ...]:
    """Keep the first source-ordered reviews up to each recommendation quota."""

    if per_recommendation <= 0:
        raise ValueError("per_recommendation must be positive")
    counts: dict[bool, int] = {True: 0, False: 0}
    selected: list[SteamReview] = []
    for review in reviews:
        if counts[review.recommended] < per_recommendation:
            selected.append(review)
            counts[review.recommended] += 1
    return tuple(selected)
