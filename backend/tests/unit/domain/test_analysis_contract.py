"""Public contract tests for versioned analysis requests and results."""

import pytest
from pydantic import ValidationError

from game_review_analyzer.domain.analysis import (
    ANALYSIS_CONTRACT_VERSION,
    AnalysisRequest,
    AnalysisResult,
    ThemeAnalysisRequest,
    ThemeAnalysisResult,
)


def test_theme_schema_avoids_unsupported_unique_items_keyword() -> None:
    schema: dict = ThemeAnalysisResult.model_json_schema()

    assert "uniqueItems" not in schema["properties"]["completed_review_revision_ids"]
    assert "uniqueItems" not in schema["$defs"]["ThemeCandidate"]["properties"][
        "supporting_review_revision_ids"
    ]


def test_analysis_contracts_are_versioned_and_reject_unknown_fields() -> None:
    request_data: dict[str, object] = {
        "schema_version": "1.0",
        "request_id": "request-1",
        "scope_sha256": "a" * 64,
        "app_id": 1145350,
        "game_title": "Hades II",
        "reviews": [
            {
                "review_revision_id": "revision-1",
                "text": "Combat feels responsive.",
            }
        ],
    }
    result_data: dict[str, object] = {
        "schema_version": "1.0",
        "request_id": "request-1",
        "scope_sha256": "a" * 64,
        "provider": "manual-codex",
        "model": "codex",
        "completed_review_revision_ids": ["revision-1"],
        "opinion_points": [],
        "themes": [],
        "mechanic_classifications": [],
    }

    assert AnalysisRequest.model_validate(request_data).schema_version == "1.0"
    assert AnalysisResult.model_validate(result_data).schema_version == "1.0"

    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate({**request_data, "schema_version": "2.0"})
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate({**result_data, "unexpected": True})


def test_theme_analysis_contract_contains_only_candidates_and_memberships() -> None:
    request_data: dict[str, object] = {
        "schema_version": "3.0",
        "request_id": "request-3",
        "scope_sha256": "b" * 64,
        "app_id": 1145350,
        "game_title": "Hades II",
        "reviews": [
            {
                "review_revision_id": "revision-1",
                "text": "Combat feels responsive.",
            },
            {
                "review_revision_id": "revision-2",
                "text": "Combat feels responsive and precise.",
            },
        ],
    }
    result_data: dict[str, object] = {
        "schema_version": "3.0",
        "request_id": "request-3",
        "scope_sha256": "b" * 64,
        "provider": "codex-cli",
        "model": "gpt-5.6-luna",
        "completed_review_revision_ids": ["revision-1", "revision-2"],
        "themes": [
            {
                "candidate_id": "responsive-combat",
                "title": "Responsive combat",
                "summary": "Players praise precise and responsive combat.",
                "polarity": "positive",
                "supporting_review_revision_ids": ["revision-1", "revision-2"],
            }
        ],
    }

    request: ThemeAnalysisRequest = ThemeAnalysisRequest.model_validate(request_data)
    result: ThemeAnalysisResult = ThemeAnalysisResult.model_validate(result_data)

    assert ANALYSIS_CONTRACT_VERSION == "3.0"
    assert request.schema_version == ANALYSIS_CONTRACT_VERSION
    assert result.themes[0].supporting_review_revision_ids == (
        "revision-1",
        "revision-2",
    )

    with pytest.raises(ValidationError):
        ThemeAnalysisResult.model_validate(
            {
                **result_data,
                "themes": [
                    {
                        **result_data["themes"][0],  # type: ignore[index]
                        "excerpt": "Combat feels responsive.",
                    }
                ],
            }
        )


def test_theme_analysis_result_rejects_duplicate_or_unknown_memberships() -> None:
    result_data: dict[str, object] = {
        "schema_version": "3.0",
        "request_id": "request-3",
        "scope_sha256": "b" * 64,
        "provider": "codex-cli",
        "model": "gpt-5.6-luna",
        "completed_review_revision_ids": ["revision-1", "revision-2"],
        "themes": [
            {
                "candidate_id": "responsive-combat",
                "title": "Responsive combat",
                "summary": "Players praise precise and responsive combat.",
                "polarity": "positive",
                "supporting_review_revision_ids": ["revision-1", "revision-1"],
            }
        ],
    }

    with pytest.raises(ValidationError):
        ThemeAnalysisResult.model_validate(result_data)

    result_data["themes"] = [
        {
            **result_data["themes"][0],  # type: ignore[index]
            "supporting_review_revision_ids": ["revision-3"],
        }
    ]
    with pytest.raises(ValidationError):
        ThemeAnalysisResult.model_validate(result_data)
