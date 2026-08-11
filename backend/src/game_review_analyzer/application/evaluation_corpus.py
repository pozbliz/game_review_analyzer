"""Selection rules for a small human-reviewed analysis evaluation subset."""

from collections.abc import Iterable
from hashlib import sha256
from itertools import islice
from typing import Literal

from game_review_analyzer.domain.reviews import SteamReview


PartitionStrategy = Literal["contiguous", "interleaved", "hashed"]


def partition_reviews_for_evaluation(
    reviews: Iterable[SteamReview],
    strategy: PartitionStrategy,
    batch_size: int,
) -> tuple[tuple[SteamReview, ...], ...]:
    """Partition one full corpus deterministically for a stability run."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    source_reviews: tuple[SteamReview, ...] = tuple(reviews)
    if not source_reviews:
        return ()
    batch_count: int = (len(source_reviews) + batch_size - 1) // batch_size
    if strategy == "interleaved":
        interleaved: list[list[SteamReview]] = [[] for _ in range(batch_count)]
        for index, review in enumerate(source_reviews):
            interleaved[index % batch_count].append(review)
        return tuple(tuple(batch) for batch in interleaved)
    ordered_reviews: tuple[SteamReview, ...] = source_reviews
    if strategy == "hashed":
        ordered_reviews = tuple(
            sorted(
                source_reviews,
                key=lambda review: sha256(review.review_id.encode("utf-8")).digest(),
            )
        )
    elif strategy != "contiguous":
        raise ValueError(f"Unknown partition strategy: {strategy}")
    return tuple(
        ordered_reviews[start : start + batch_size]
        for start in range(0, len(ordered_reviews), batch_size)
    )


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
