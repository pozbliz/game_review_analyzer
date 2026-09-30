"""Apply deterministic Main Report review batching rules."""

from collections.abc import Iterator

from game_review_analyzer.domain.reviews import SteamReview


def pack_review_batches(
    revision_ids: tuple[int, ...],
    revisions: dict[int, SteamReview],
    character_limit: int,
    review_limit: int = 250,
) -> Iterator[tuple[int, ...]]:
    """Pack complete reviews by character capacity and the 250-review ceiling."""

    batch: list[int] = []
    characters: int = 0
    for revision_id in revision_ids:
        text_length: int = len(revisions[revision_id].text)
        if batch and (
            len(batch) >= min(review_limit, 250)
            or characters + text_length > character_limit
        ):
            yield tuple(batch)
            batch = []
            characters = 0
        batch.append(revision_id)
        characters += text_length
    if batch:
        yield tuple(batch)
