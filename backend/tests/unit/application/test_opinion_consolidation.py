"""Deterministic shared-Theme consolidation tests."""

from game_review_analyzer.application.opinion_consolidation import (
    consolidate_opinion_points,
)
from game_review_analyzer.domain.analysis import (
    AnalysisRequest,
    AnalysisSourceReview,
    ExtractedOpinionPoint,
    OpinionSentiment,
)


def test_canonical_subjects_form_shared_themes_without_another_model_call() -> None:
    request = AnalysisRequest(
        schema_version="1.0",
        request_id="run-1",
        scope_sha256="a" * 64,
        app_id=10,
        game_title="Game",
        reviews=(
            AnalysisSourceReview(review_revision_id="early-1", text="[]"),
            AnalysisSourceReview(review_revision_id="recent-1", text="[]"),
        ),
    )
    points = (
        extracted("one", "early-1", "responsive combat", "Combat responds."),
        extracted("two", "recent-1", " Responsive   Combat ", "Fights respond."),
    )

    result = consolidate_opinion_points(
        request,
        points,
        provider="codex-cli",
        model="gpt-5.6-luna",
    )

    assert len(result.themes) == 1
    assert result.themes[0].title == "Responsive combat"
    assert result.themes[0].opinion_point_ids == ("one", "two")
    assert {point.supports_theme_id for point in result.opinion_points} == {
        result.themes[0].id
    }


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
