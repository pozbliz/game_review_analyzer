"""Calculate deterministic report metrics from validated Theme memberships."""

from collections.abc import Iterable

from game_review_analyzer.domain.analysis import ThemePolarity
from game_review_analyzer.domain.reports import (
    AggregateThemeMetric,
    AggregateThemeMetrics,
    ThemeDefinition,
    ThemeMembership,
    ThemeMetricPolicy,
)


def calculate_aggregate_theme_metrics(
    scope_review_revision_ids: Iterable[int],
    oldest_review_revision_ids: Iterable[int],
    newest_review_revision_ids: Iterable[int],
    themes: Iterable[ThemeDefinition],
    memberships: Iterable[ThemeMembership],
    policy: ThemeMetricPolicy,
) -> AggregateThemeMetrics:
    """Calculate Version 3 support and visible Theme rankings locally."""

    scope_ids: tuple[int, ...] = tuple(scope_review_revision_ids)
    scope_id_set: set[int] = set(scope_ids)
    oldest_ids: set[int] = set(oldest_review_revision_ids)
    newest_ids: set[int] = set(newest_review_revision_ids)
    if not scope_ids or len(scope_ids) != len(scope_id_set):
        raise ValueError("scope Review Revision identifiers must be non-empty and unique")
    if oldest_ids & newest_ids or oldest_ids | newest_ids != scope_id_set:
        raise ValueError("Theme metric cohorts must be non-overlapping and cover the scope")

    theme_items: tuple[ThemeDefinition, ...] = tuple(themes)
    theme_by_id: dict[str, ThemeDefinition] = {
        theme.theme_id: theme for theme in theme_items
    }
    if len(theme_by_id) != len(theme_items):
        raise ValueError("Theme identifiers must be unique")
    support_by_theme: dict[str, set[int]] = {
        theme.theme_id: set() for theme in theme_items
    }
    for membership in memberships:
        if membership.theme_id not in theme_by_id:
            raise ValueError("Theme Membership references an unknown Theme")
        if membership.review_revision_id not in scope_id_set:
            raise ValueError("Theme Membership references a review outside the scope")
        support_by_theme[membership.theme_id].add(membership.review_revision_id)

    metrics: list[AggregateThemeMetric] = []
    for theme in theme_items:
        support_ids: set[int] = support_by_theme[theme.theme_id]
        oldest_count: int = len(support_ids & oldest_ids)
        newest_count: int = len(support_ids & newest_ids)
        oldest_percentage: float = (
            oldest_count / len(oldest_ids) * 100 if oldest_ids else 0
        )
        newest_percentage: float = (
            newest_count / len(newest_ids) * 100 if newest_ids else 0
        )
        metrics.append(
            AggregateThemeMetric(
                theme_id=theme.theme_id,
                polarity=theme.polarity,
                support_count=len(support_ids),
                total_support_percentage=len(support_ids) / len(scope_ids) * 100,
                oldest_support_percentage=oldest_percentage,
                newest_support_percentage=newest_percentage,
                percentage_point_difference=newest_percentage - oldest_percentage,
            )
        )

    ranked: list[AggregateThemeMetric] = sorted(
        metrics,
        key=lambda metric: (
            -max(metric.oldest_support_percentage, metric.newest_support_percentage),
            metric.theme_id,
        ),
    )
    visible: list[AggregateThemeMetric] = [
        metric
        for metric in ranked
        if max(metric.oldest_support_percentage, metric.newest_support_percentage)
        >= policy.minimum_support_percentage
        and metric.support_count >= policy.minimum_support_count
    ]
    return AggregateThemeMetrics(
        all_themes=tuple(metrics),
        positive_headlines=tuple(
            metric for metric in visible if metric.polarity == ThemePolarity.POSITIVE
        )[: policy.maximum_headlines_per_polarity],
        negative_headlines=tuple(
            metric for metric in visible if metric.polarity == ThemePolarity.NEGATIVE
        )[: policy.maximum_headlines_per_polarity],
    )
