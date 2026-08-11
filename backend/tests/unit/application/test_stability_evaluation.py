"""Validation tests for repeated headline-Theme stability runs."""

import json
from typing import Any

import pytest

from game_review_analyzer.application.stability_evaluation import (
    StabilityValidationError,
    validate_stability_result,
)


def test_stability_result_is_bound_to_scope_and_exact_evidence() -> None:
    run_input: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": "hades-ii-contiguous",
        "game_case_id": "hades-ii",
        "app_id": 1145350,
        "game_title": "Hades II",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "medium",
        "partition_strategy": "contiguous",
        "review_count": 2,
        "batches": [
            {
                "batch_id": "batch-001",
                "reviews": [
                    {
                        "review_revision_id": "revision-1",
                        "text": "Combat is responsive.",
                    },
                    {
                        "review_revision_id": "revision-2",
                        "text": "Fights feel responsive.",
                    },
                ],
            }
        ],
    }
    valid_result: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": "hades-ii-contiguous",
        "game_case_id": "hades-ii",
        "app_id": 1145350,
        "model": "gpt-5.6-luna",
        "reasoning_effort": "medium",
        "partition_strategy": "contiguous",
        "review_count": 2,
        "themes": [
            {
                "theme_key": "combat-responsiveness-positive",
                "title": "Responsive combat",
                "summary": "Players describe combat as responsive.",
                "polarity": "positive",
                "primary_category": "Gameplay and mechanics",
                "technical": False,
                "coherence_score": 0.95,
                "supporting_review_revision_ids": ["revision-1", "revision-2"],
                "representative_excerpts": [
                    {
                        "review_revision_id": "revision-1",
                        "excerpt": "Combat is responsive",
                    },
                    {
                        "review_revision_id": "revision-2",
                        "excerpt": "Fights feel responsive",
                    },
                ],
            }
        ],
    }

    assert len(validate_stability_result(run_input, json.dumps(valid_result)).themes) == 1

    invalid_results: tuple[tuple[str, dict[str, Any]], ...] = (
        ("scope_mismatch", {**valid_result, "run_id": "other-run"}),
        (
            "unknown_review_revision",
            {
                **valid_result,
                "themes": [
                    {
                        **valid_result["themes"][0],
                        "supporting_review_revision_ids": ["revision-1", "unknown"],
                    }
                ],
            },
        ),
        (
            "non_matching_excerpt",
            {
                **valid_result,
                "themes": [
                    {
                        **valid_result["themes"][0],
                        "representative_excerpts": [
                            {
                                "review_revision_id": "revision-1",
                                "excerpt": "Invented evidence",
                            }
                        ],
                    }
                ],
            },
        ),
    )
    for expected_code, invalid_result in invalid_results:
        with pytest.raises(StabilityValidationError) as raised:
            validate_stability_result(run_input, json.dumps(invalid_result))
        assert raised.value.code == expected_code
