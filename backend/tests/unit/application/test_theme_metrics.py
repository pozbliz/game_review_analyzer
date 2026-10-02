"""Tests for deterministic aggregate Theme metrics."""

from game_review_analyzer.application.theme_metrics import (
    calculate_aggregate_theme_metrics,
)
from game_review_analyzer.domain.analysis import ThemePolarity
from game_review_analyzer.domain.reports import (
    AggregateThemeMetrics,
    ThemeDefinition,
    ThemeMembership,
    ThemeMetricPolicy,
)


def test_aggregate_metrics_use_distinct_memberships_and_cohort_denominators() -> None:
    themes: tuple[ThemeDefinition, ...] = (
        theme("positive-oldest", ThemePolarity.POSITIVE),
        theme("positive-newest", ThemePolarity.POSITIVE),
        theme("negative-both", ThemePolarity.NEGATIVE),
        theme("hidden", ThemePolarity.NEGATIVE),
    )
    memberships: tuple[ThemeMembership, ...] = (
        ThemeMembership(theme_id="positive-oldest", review_revision_id=1),
        ThemeMembership(theme_id="positive-oldest", review_revision_id=1),
        ThemeMembership(theme_id="positive-newest", review_revision_id=21),
        ThemeMembership(theme_id="negative-both", review_revision_id=2),
        ThemeMembership(theme_id="negative-both", review_revision_id=22),
    )

    metrics: AggregateThemeMetrics = calculate_aggregate_theme_metrics(
        range(1, 41),
        range(1, 21),
        range(21, 41),
        themes,
        memberships,
        policy(),
    )

    oldest = next(item for item in metrics.all_themes if item.theme_id == "positive-oldest")
    both = next(item for item in metrics.all_themes if item.theme_id == "negative-both")
    assert (oldest.support_count, oldest.total_support_percentage) == (1, 2.5)
    assert (oldest.oldest_support_percentage, oldest.newest_support_percentage) == (5, 0)
    assert oldest.percentage_point_difference == -5
    assert (both.support_count, both.total_support_percentage) == (2, 5)
    assert tuple(item.theme_id for item in metrics.positive_headlines) == (
        "positive-newest",
        "positive-oldest",
    )
    assert tuple(item.theme_id for item in metrics.negative_headlines) == ("negative-both",)


def test_aggregate_metrics_cap_each_polarity_and_allow_no_visible_themes() -> None:
    themes: tuple[ThemeDefinition, ...] = tuple(
        theme(f"positive-{index}", ThemePolarity.POSITIVE) for index in range(3)
    ) + (theme("negative-0", ThemePolarity.NEGATIVE),)
    memberships: tuple[ThemeMembership, ...] = tuple(
        ThemeMembership(theme_id=item.theme_id, review_revision_id=index + 1)
        for index, item in enumerate(themes)
    )
    metric_policy: ThemeMetricPolicy = policy(maximum_headlines_per_polarity=2)

    metrics: AggregateThemeMetrics = calculate_aggregate_theme_metrics(
        range(1, 21), range(1, 11), range(11, 21), themes, memberships, metric_policy
    )
    empty: AggregateThemeMetrics = calculate_aggregate_theme_metrics(
        range(1, 21), range(1, 11), range(11, 21), themes, (), metric_policy
    )

    assert len(metrics.positive_headlines) == 2
    assert tuple(item.theme_id for item in metrics.negative_headlines) == ("negative-0",)
    assert empty.positive_headlines == ()
    assert empty.negative_headlines == ()


def theme(theme_id: str, polarity: ThemePolarity) -> ThemeDefinition:
    return ThemeDefinition(
        theme_id=theme_id,
        title=theme_id,
        summary=f"Summary for {theme_id}.",
        polarity=polarity,
    )


def policy(maximum_headlines_per_polarity: int = 10) -> ThemeMetricPolicy:
    return ThemeMetricPolicy(
        minimum_support_count=1,
        minimum_support_percentage=5,
        technical_minimum_support_count=1,
        technical_minimum_support_percentage=5,
        maximum_headlines_per_polarity=maximum_headlines_per_polarity,
    )
