"""Deterministically consolidate canonical extracted subjects into shared Themes."""

from hashlib import sha256

from game_review_analyzer.domain.analysis import (
    AnalysisRequest,
    AnalysisResult,
    ExtractedOpinionPoint,
    OpinionPoint,
    OpinionSentiment,
    Theme,
    ThemeCategory,
    ThemePolarity,
)


TECHNICAL_WORDS: frozenset[str] = frozenset(
    {"bug", "crash", "fps", "latency", "performance", "stutter", "freeze"}
)


def consolidate_opinion_points(
    request: AnalysisRequest,
    extracted_points: tuple[ExtractedOpinionPoint, ...],
    *,
    provider: str,
    model: str,
) -> AnalysisResult:
    """Group recurring canonical subjects and preserve every validated point."""

    groups: dict[tuple[OpinionSentiment, str], list[ExtractedOpinionPoint]] = {}
    for point in extracted_points:
        if point.sentiment == OpinionSentiment.NEUTRAL:
            continue
        key: tuple[OpinionSentiment, str] = (
            point.sentiment,
            canonical_subject(point.subject),
        )
        groups.setdefault(key, []).append(point)

    themes: list[Theme] = []
    theme_id_by_key: dict[tuple[OpinionSentiment, str], str] = {}
    for (sentiment, subject), points in sorted(
        groups.items(), key=lambda item: (item[0][1], item[0][0].value)
    ):
        if len({point.review_revision_id for point in points}) < 2:
            continue
        theme_id: str = "theme-" + sha256(
            f"{sentiment.value}:{subject}".encode("utf-8")
        ).hexdigest()[:16]
        theme_id_by_key[(sentiment, subject)] = theme_id
        technical: bool = bool(set(subject.split()) & TECHNICAL_WORDS)
        themes.append(
            Theme(
                id=theme_id,
                title=subject.capitalize(),
                summary=f"Players mention {subject} {sentiment.value}ly.",
                polarity=ThemePolarity(sentiment.value),
                primary_category=ThemeCategory.GAME_SPECIFIC,
                related_categories=(),
                opinion_point_ids=tuple(point.id for point in points),
                technical=technical,
                opposes_theme_id=None,
            )
        )

    theme_by_id: dict[str, Theme] = {theme.id: theme for theme in themes}
    for (sentiment, subject), theme_id in theme_id_by_key.items():
        opposite: OpinionSentiment = (
            OpinionSentiment.NEGATIVE
            if sentiment == OpinionSentiment.POSITIVE
            else OpinionSentiment.POSITIVE
        )
        opposing_id: str | None = theme_id_by_key.get((opposite, subject))
        if opposing_id is not None:
            theme_by_id[theme_id] = theme_by_id[theme_id].model_copy(
                update={"opposes_theme_id": opposing_id}
            )

    opinion_points: tuple[OpinionPoint, ...] = tuple(
        OpinionPoint(
            **point.model_dump(exclude={"subject"}),
            subject=canonical_subject(point.subject),
            supports_theme_id=theme_id_by_key.get(
                (point.sentiment, canonical_subject(point.subject))
            ),
        )
        for point in extracted_points
    )
    return AnalysisResult(
        schema_version="1.0",
        request_id=request.request_id,
        scope_sha256=request.scope_sha256,
        provider=provider,
        model=model,
        completed_review_revision_ids=tuple(
            review.review_revision_id for review in request.reviews
        ),
        opinion_points=opinion_points,
        themes=tuple(theme_by_id[theme.id] for theme in themes),
        mechanic_classifications=(),
    )


def canonical_subject(subject: str) -> str:
    """Normalize provider whitespace and casing without guessing semantics."""

    return " ".join(subject.casefold().split())
