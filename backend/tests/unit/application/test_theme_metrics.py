"""Deterministic Theme metric tests."""

import json
from pathlib import Path
from typing import Any

from game_review_analyzer.application.theme_metrics import (
    ThemeMetricPolicy,
    calculate_theme_metrics,
)
from game_review_analyzer.domain.analysis import OpinionPoint, Theme


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
