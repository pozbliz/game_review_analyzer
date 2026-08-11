"""Integrity checks for the provider-independent synthetic evaluation fixture."""

import json
from pathlib import Path
from typing import Any


def test_synthetic_evaluation_fixture_has_exact_and_connected_gold_labels() -> None:
    fixture_path: Path = (
        Path(__file__).parents[1] / "fixtures" / "analysis_evaluation" / "synthetic_v1.json"
    )
    corpus: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert corpus["schema_version"] == "1.0"
    assert corpus["corpus_kind"] == "synthetic_conformance"
    assert len(corpus["games"]) >= 3

    for game in corpus["games"]:
        reviews: dict[str, dict[str, Any]] = {
            review["review_revision_id"]: review for review in game["reviews"]
        }
        points: dict[str, dict[str, Any]] = {
            point["id"]: point for point in game["opinion_points"]
        }
        themes: dict[str, dict[str, Any]] = {
            theme["id"]: theme for theme in game["themes"]
        }

        for point in points.values():
            assert point["excerpt"] in reviews[point["review_revision_id"]]["text"]
            if point["sentiment"] == "neutral":
                assert point["supports_theme_id"] is None
            else:
                assert point["supports_theme_id"] in themes

        for theme in themes.values():
            supporting_reviews: set[str] = {
                points[point_id]["review_revision_id"]
                for point_id in theme["opinion_point_ids"]
            }
            assert len(supporting_reviews) >= 2
            opposing_id: str | None = theme["opposes_theme_id"]
            if opposing_id:
                assert themes[opposing_id]["opposes_theme_id"] == theme["id"]

        for classification in game["mechanic_classifications"]:
            assert classification["review_revision_id"] in reviews
            assert classification["classification"] in {"liked", "disliked", "mixed"}
