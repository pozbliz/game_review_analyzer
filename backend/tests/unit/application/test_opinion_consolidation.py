"""Specific Opinion Point filtering tests."""

from game_review_analyzer.application.opinion_consolidation import (
    exclude_known_generic_opinion_points,
)
from game_review_analyzer.domain.analysis import (
    ExtractedOpinionPoint,
    OpinionSentiment,
)


def test_generic_subjects_do_not_reach_semantic_consolidation() -> None:
    points = (
        extracted("generic-1", "one", "game quality", "Amazing game."),
        extracted("generic-2", "two", "gameplay", "The gameplay is fun."),
        extracted("generic-3", "three", "story", "The story is good."),
        extracted("specific-1", "four", "harpoon timing", "Harpoon timing feels responsive."),
        extracted("specific-2", "five", "dialogue pacing", "Dialogue pacing feels unnatural."),
    )

    filtered = exclude_known_generic_opinion_points(points)

    assert tuple(point.id for point in filtered) == ("specific-1", "specific-2")


def extracted(
    identifier: str,
    review_id: str,
    subject: str,
    excerpt: str,
) -> ExtractedOpinionPoint:
    return ExtractedOpinionPoint(
        id=identifier,
        review_revision_id=review_id,
        excerpt=excerpt,
        sentiment=OpinionSentiment.POSITIVE,
        subject=subject,
    )
