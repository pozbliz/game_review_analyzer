"""Validation tests for repeated headline-Theme stability runs."""

import json
from typing import Any

import pytest

from game_review_analyzer.application.stability_evaluation import (
    StabilityValidationError,
    apply_stability_evidence_repair,
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
        ("malformed_result", {**valid_result, "themes": []}),
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


def test_evidence_repair_changes_only_the_requested_theme_evidence() -> None:
    run_input: dict[str, Any] = {
        "run_id": "hades-ii-contiguous",
        "game_case_id": "hades-ii",
        "app_id": 1145350,
        "model": "gpt-5.6-luna",
        "reasoning_effort": "medium",
        "partition_strategy": "contiguous",
        "review_count": 2,
        "batches": [
            {
                "reviews": [
                    {"review_revision_id": "revision-1", "text": "Very polished."},
                    {"review_revision_id": "revision-2", "text": "Loads of content."},
                ]
            }
        ],
    }
    original_result: dict[str, Any] = {
        "schema_version": "1.0",
        **{key: run_input[key] for key in (
            "run_id",
            "game_case_id",
            "app_id",
            "model",
            "reasoning_effort",
            "partition_strategy",
            "review_count",
        )},
        "themes": [
            {
                "theme_key": "polished-sequel",
                "title": "A polished sequel",
                "summary": "Players praise its polish and breadth.",
                "polarity": "positive",
                "primary_category": "Content, variety, and replayability",
                "technical": False,
                "coherence_score": 0.9,
                "supporting_review_revision_ids": ["revision-1", "revision-2"],
                "representative_excerpts": [
                    {"review_revision_id": "revision-1", "excerpt": "very polished"}
                ],
            }
        ],
    }
    repair: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": "hades-ii-contiguous",
        "repairs": [
            {
                "theme_key": "polished-sequel",
                "representative_excerpts": [
                    {"review_revision_id": "revision-1", "excerpt": "Very polished"}
                ],
            }
        ],
    }

    repaired = apply_stability_evidence_repair(
        run_input,
        json.dumps(original_result),
        json.dumps(repair),
        {"polished-sequel"},
    )

    assert repaired.themes[0].representative_excerpts[0].excerpt == "Very polished"
    assert repaired.themes[0].supporting_review_revision_ids == (
        "revision-1",
        "revision-2",
    )


def test_evidence_repair_rejects_unrequested_or_non_exact_changes() -> None:
    run_input: dict[str, Any] = {
        "run_id": "run-1",
        "game_case_id": "game-1",
        "app_id": 1,
        "model": "gpt-5.6-luna",
        "reasoning_effort": "medium",
        "partition_strategy": "hashed",
        "review_count": 2,
        "batches": [{"reviews": [
            {"review_revision_id": "r1", "text": "Exact evidence."},
            {"review_revision_id": "r2", "text": "More exact evidence."},
        ]}],
    }
    original: dict[str, Any] = {
        "schema_version": "1.0",
        **{key: run_input[key] for key in (
            "run_id",
            "game_case_id",
            "app_id",
            "model",
            "reasoning_effort",
            "partition_strategy",
            "review_count",
        )},
        "themes": [{
            "theme_key": "theme-1",
            "title": "Theme",
            "summary": "Summary",
            "polarity": "positive",
            "primary_category": "Game-specific",
            "technical": False,
            "coherence_score": 1,
            "supporting_review_revision_ids": ["r1", "r2"],
            "representative_excerpts": [
                {"review_revision_id": "r1", "excerpt": "exact evidence"}
            ],
        }],
    }

    invalid_repairs: tuple[tuple[str, set[str], dict[str, Any]], ...] = (
        (
            "repair_scope_mismatch",
            {"theme-1"},
            {"theme_key": "theme-2", "representative_excerpts": [
                {"review_revision_id": "r1", "excerpt": "Exact evidence"}
            ]},
        ),
        (
            "unknown_theme",
            {"theme-2"},
            {"theme_key": "theme-2", "representative_excerpts": [
                {"review_revision_id": "r1", "excerpt": "Exact evidence"}
            ]},
        ),
        (
            "non_matching_excerpt",
            {"theme-1"},
            {"theme_key": "theme-1", "representative_excerpts": [
                {"review_revision_id": "r1", "excerpt": "Invented evidence"}
            ]},
        ),
        (
            "malformed_repair",
            {"theme-1"},
            {
                "theme_key": "theme-1",
                "title": "Unauthorized change",
                "representative_excerpts": [
                    {"review_revision_id": "r1", "excerpt": "Exact evidence"}
                ],
            },
        ),
    )
    for expected_code, rejected_keys, item in invalid_repairs:
        repair: dict[str, Any] = {
            "schema_version": "1.0",
            "run_id": "run-1",
            "repairs": [item],
        }
        with pytest.raises(StabilityValidationError) as raised:
            apply_stability_evidence_repair(
                run_input,
                json.dumps(original),
                json.dumps(repair),
                rejected_keys,
            )
        assert raised.value.code == expected_code
