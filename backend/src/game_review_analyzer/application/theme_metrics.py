"""Calculate deterministic report metrics from validated Theme memberships."""

from collections.abc import Iterable

from game_review_analyzer.domain.analysis import (
    OpinionPoint,
    OpinionSentiment,
    Theme,
    ThemePolarity,
)
from game_review_analyzer.domain.reports import (
    MixedReceptionMetric,
    ThemeMetric,
    ThemeMetricPolicy,
    ThemeMetrics,
)


def calculate_theme_metrics(
    scope_review_revision_ids: Iterable[str],
    opinion_points: Iterable[OpinionPoint],
    themes: Iterable[Theme],
    policy: ThemeMetricPolicy,
) -> ThemeMetrics:
    """Calculate counts, percentages, rankings, and opposing reception."""

    scope_ids: tuple[str, ...] = tuple(scope_review_revision_ids)
    scope_id_set: set[str] = set(scope_ids)
    if not scope_ids or len(scope_ids) != len(scope_id_set):
        raise ValueError("scope Review Revision identifiers must be non-empty and unique")
    theme_items: tuple[Theme, ...] = tuple(themes)
    theme_by_id: dict[str, Theme] = {theme.id: theme for theme in theme_items}
    if len(theme_by_id) != len(theme_items):
        raise ValueError("Theme identifiers must be unique")
    support_by_theme: dict[str, set[str]] = {theme.id: set() for theme in theme_items}
    for point in opinion_points:
        if point.review_revision_id not in scope_id_set:
            raise ValueError("Opinion Point references a review outside the scope")
        if point.supports_theme_id is None:
            continue
        theme: Theme | None = theme_by_id.get(point.supports_theme_id)
        if theme is None:
            raise ValueError("Opinion Point references an unknown Theme")
        if point.sentiment == OpinionSentiment.NEUTRAL:
            raise ValueError("Neutral Opinion Points cannot support Themes")
        if point.sentiment.value != theme.polarity.value:
            raise ValueError("Opinion Point sentiment does not match Theme polarity")
        support_by_theme[theme.id].add(point.review_revision_id)

    metric_by_id: dict[str, ThemeMetric] = {}
    for theme in theme_items:
        support_count: int = len(support_by_theme[theme.id])
        metric_by_id[theme.id] = ThemeMetric(
            theme_id=theme.id,
            polarity=theme.polarity,
            primary_category=theme.primary_category,
            related_categories=theme.related_categories,
            technical=theme.technical,
            support_count=support_count,
            support_percentage=support_count / len(scope_ids) * 100,
        )

    ranked: list[ThemeMetric] = sorted(
        metric_by_id.values(), key=lambda metric: (-metric.support_count, metric.theme_id)
    )
    design_headlines: list[ThemeMetric] = [
        metric
        for metric in ranked
        if not metric.technical
        and metric.support_count >= policy.minimum_support_count
        and metric.support_percentage >= policy.minimum_support_percentage
    ]
    positive: tuple[ThemeMetric, ...] = tuple(
        metric
        for metric in design_headlines
        if metric.polarity == ThemePolarity.POSITIVE
    )[: policy.maximum_headlines_per_polarity]
    negative: tuple[ThemeMetric, ...] = tuple(
        metric
        for metric in design_headlines
        if metric.polarity == ThemePolarity.NEGATIVE
    )[: policy.maximum_headlines_per_polarity]
    technical: tuple[ThemeMetric, ...] = tuple(
        metric
        for metric in ranked
        if metric.technical
        and metric.support_count >= policy.technical_minimum_support_count
        and metric.support_percentage >= policy.technical_minimum_support_percentage
    )

    mixed: list[MixedReceptionMetric] = []
    for theme in theme_items:
        opposing_id: str | None = theme.opposes_theme_id
        if opposing_id is None or theme.id > opposing_id:
            continue
        opposing: Theme | None = theme_by_id.get(opposing_id)
        if opposing is None or opposing.opposes_theme_id != theme.id:
            raise ValueError("Opposing Themes must be reciprocal")
        positive_theme: Theme = theme if theme.polarity == ThemePolarity.POSITIVE else opposing
        negative_theme: Theme = opposing if positive_theme is theme else theme
        positive_reviews: set[str] = support_by_theme[positive_theme.id]
        negative_reviews: set[str] = support_by_theme[negative_theme.id]
        opinionated_reviews: set[str] = positive_reviews | negative_reviews
        opinionated_count: int = len(opinionated_reviews)
        if opinionated_count == 0:
            continue
        liked_count: int = len(positive_reviews - negative_reviews)
        disliked_count: int = len(negative_reviews - positive_reviews)
        mixed_count: int = len(positive_reviews & negative_reviews)
        mixed.append(
            MixedReceptionMetric(
                positive_theme_id=positive_theme.id,
                negative_theme_id=negative_theme.id,
                liked_count=liked_count,
                disliked_count=disliked_count,
                mixed_count=mixed_count,
                opinionated_review_count=opinionated_count,
                mentioned_review_count=opinionated_count,
                scope_review_count=len(scope_ids),
                liked_percentage=liked_count / opinionated_count * 100,
                disliked_percentage=disliked_count / opinionated_count * 100,
                mixed_percentage=mixed_count / opinionated_count * 100,
                mentioned_percentage=opinionated_count / len(scope_ids) * 100,
            )
        )
    return ThemeMetrics(
        all_themes=tuple(metric_by_id[theme.id] for theme in theme_items),
        positive_headlines=positive,
        negative_headlines=negative,
        technical_themes=technical,
        mixed_reception=tuple(mixed),
    )
