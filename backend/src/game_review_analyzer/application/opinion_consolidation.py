"""Keep concrete extracted opinions for semantic Theme consolidation."""

from game_review_analyzer.domain.analysis import (
    ExtractedOpinionPoint,
)


GENERIC_SUBJECTS: frozenset[str] = frozenset(
    {
        "game",
        "game quality",
        "gameplay",
        "graphics",
        "overall experience",
        "overall game quality",
        "overall recommendation",
        "story",
        "visuals",
    }
)


def exclude_known_generic_opinion_points(
    points: tuple[ExtractedOpinionPoint, ...],
) -> tuple[ExtractedOpinionPoint, ...]:
    """Remove known generic subjects before semantic Theme consolidation."""

    return tuple(
        point
        for point in points
        if canonical_subject(point.subject) not in GENERIC_SUBJECTS
    )


def canonical_subject(subject: str) -> str:
    """Normalize provider whitespace and casing without guessing semantics."""

    return " ".join(subject.casefold().split())
