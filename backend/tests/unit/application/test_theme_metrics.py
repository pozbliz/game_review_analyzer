"""Deterministic Theme metric tests."""

import json
from pathlib import Path
from typing import Any

from game_review_analyzer.application.theme_metrics import (
    calculate_filtered_theme_metrics,
    calculate_theme_metrics,
)
from game_review_analyzer.domain.analysis import OpinionPoint, Theme
from game_review_analyzer.domain.reports import EvidenceFilterQuery, ThemeMetricPolicy
from game_review_analyzer.domain.reviews import SteamReview


def test_metrics_use_distinct_reviews_global_caps_and_separate_technical_themes() -> None:
    fixture_path: Path = (
        Path(__file__).parents[2]
        / "fixtures"
        / "analysis_evaluation"
        / "synthetic_v1.json"
    )
    corpus: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    reviews: list[str] = []
    points: list[OpinionPoint] = []
    themes: list[Theme] = []
    for game in corpus["games"]:
        reviews.extend(review["review_revision_id"] for review in game["reviews"])
        points.extend(OpinionPoint.model_validate(point) for point in game["opinion_points"])
        themes.extend(Theme.model_validate(theme) for theme in game["themes"])

    metrics = calculate_theme_metrics(
        reviews,
        points,
        themes,
        ThemeMetricPolicy(
            minimum_support_count=2,
            minimum_support_percentage=0,
            technical_minimum_support_count=3,
            technical_minimum_support_percentage=0,
            maximum_headlines_per_polarity=2,
        ),
    )

    assert [theme.theme_id for theme in metrics.positive_headlines] == [
        "ev-t1",
        "mv-t1",
    ]
    assert [theme.theme_id for theme in metrics.negative_headlines] == [
        "ev-t2",
        "mv-t2",
    ]
    assert [theme.theme_id for theme in metrics.technical_themes] == ["sf-t1"]
    assert metrics.positive_headlines[0].support_count == 3
    assert metrics.positive_headlines[0].support_percentage == 30
    assert metrics.positive_headlines[0].primary_category.value == (
        "Controls, interface, and onboarding"
    )
    mixed = metrics.mixed_reception[0]
    assert (mixed.liked_count, mixed.disliked_count, mixed.mixed_count) == (2, 1, 1)
    assert mixed.opinionated_review_count == 4
    assert mixed.mentioned_review_count == 4
    assert mixed.scope_review_count == 10


def test_filtered_metrics_use_only_matching_reviews_and_new_denominator() -> None:
    reviews: tuple[SteamReview, ...] = (
        review("r1", True, 60, 1_700_000_000),
        review("r2", True, 240, 1_700_000_001),
        review("r3", False, 360, 1_700_000_002),
    )
    points: tuple[OpinionPoint, ...] = (
        point("p1", "r1", "positive", "positive-theme"),
        point("p2", "r2", "positive", "positive-theme"),
        point("p3", "r3", "negative", "negative-theme"),
    )
    themes: tuple[Theme, ...] = (
        theme("positive-theme", "positive", ("p1", "p2")),
        theme("negative-theme", "negative", ("p3",)),
    )
    policy = ThemeMetricPolicy(
        minimum_support_count=1,
        minimum_support_percentage=0,
        technical_minimum_support_count=1,
        technical_minimum_support_percentage=0,
    )

    metrics = calculate_filtered_theme_metrics(
        reviews,
        points,
        themes,
        policy,
        EvidenceFilterQuery(
            recommendation="recommended", minimum_playtime_minutes=120
        ),
    )

    assert [(item.theme_id, item.support_count) for item in metrics.all_themes] == [
        ("positive-theme", 1),
        ("negative-theme", 0),
    ]
    assert metrics.positive_headlines[0].support_percentage == 100
    assert metrics.negative_headlines == ()


def test_filtered_metrics_return_zero_support_when_no_reviews_match() -> None:
    reviews: tuple[SteamReview, ...] = (review("r1", True, 60, 100),)
    points: tuple[OpinionPoint, ...] = (
        point("p1", "r1", "positive", "positive-theme"),
    )
    themes: tuple[Theme, ...] = (
        theme("positive-theme", "positive", ("p1",)),
    )
    policy = ThemeMetricPolicy(
        minimum_support_count=1,
        minimum_support_percentage=0,
        technical_minimum_support_count=1,
        technical_minimum_support_percentage=0,
    )

    metrics = calculate_filtered_theme_metrics(
        reviews,
        points,
        themes,
        policy,
        EvidenceFilterQuery(review_created_from=101),
    )

    assert metrics.all_themes[0].support_count == 0
    assert metrics.all_themes[0].support_percentage == 0
    assert metrics.positive_headlines == ()


def review(
    review_id: str,
    recommended: bool,
    playtime_at_review_minutes: int,
    source_created_at: int,
) -> SteamReview:
    return SteamReview(
        review_id=review_id,
        language="english",
        text="Review text",
        source_created_at=source_created_at,
        source_updated_at=source_created_at,
        recommended=recommended,
        votes_helpful=0,
        votes_funny=0,
        weighted_vote_score=0,
        steam_purchase=True,
        received_for_free=False,
        written_during_early_access=False,
        playtime_forever_minutes=playtime_at_review_minutes + 60,
        playtime_at_review_minutes=playtime_at_review_minutes,
    )


def point(
    point_id: str,
    review_id: str,
    sentiment: str,
    theme_id: str,
) -> OpinionPoint:
    return OpinionPoint(
        id=point_id,
        review_revision_id=review_id,
        excerpt="Evidence",
        sentiment=sentiment,
        subject="subject",
        supports_theme_id=theme_id,
    )


def theme(theme_id: str, polarity: str, point_ids: tuple[str, ...]) -> Theme:
    return Theme(
        id=theme_id,
        title=theme_id,
        summary="Summary",
        polarity=polarity,
        primary_category="Gameplay and mechanics",
        related_categories=(),
        opinion_point_ids=point_ids,
        technical=False,
        opposes_theme_id=None,
    )
