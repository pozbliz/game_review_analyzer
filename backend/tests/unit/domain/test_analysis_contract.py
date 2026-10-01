"""Public contract tests for versioned analysis requests and results."""

import pytest
from pydantic import ValidationError

from game_review_analyzer.domain.analysis import (
    ANALYSIS_CONTRACT_VERSION,
    AnalysisRequest,
    AnalysisResult,
    ThemeAnalysisOutput,
    ThemeAnalysisRequest,
    ThemeAnalysisResult,
    ThemeMergeOutput,
    ThemeMergeResult,
)


def test_provider_outputs_contain_only_semantic_fields() -> None:
    map_schema: dict = ThemeAnalysisOutput.model_json_schema()
    merge_schema: dict = ThemeMergeOutput.model_json_schema()

    assert set(map_schema["properties"]) == {"themes"}
    assert set(map_schema["$defs"]["ThemeCandidateOutput"]["properties"]) == {
        "title",
        "summary",
        "polarity",
        "supporting_review_positions",
    }
    assert set(merge_schema["properties"]) == {"new_themes", "assignments"}
    assert set(merge_schema["$defs"]["ThemeMergeThemeOutput"]["properties"]) == {
        "title",
        "summary",
        "polarity",
    }
    assert set(
        merge_schema["$defs"]["ThemeMergeAssignmentOutput"]["properties"]
    ) == {"established_theme_position", "new_theme_position"}


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
        "schema_version": "3.1",
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
        "schema_version": "3.1",
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

    assert ANALYSIS_CONTRACT_VERSION == "3.1"
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
        "schema_version": "3.1",
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


def test_theme_merge_result_rejects_duplicate_candidate_assignments() -> None:
    result_data: dict[str, object] = {
        "schema_version": "3.1",
        "request_id": "merge-1",
        "scope_sha256": "c" * 64,
        "provider": "codex-cli",
        "model": "gpt-5.6-luna",
        "themes": [{
            "theme_id": "combat",
            "title": "Combat",
            "summary": "Players praise combat.",
            "polarity": "positive",
        }],
        "assignments": [
            {"candidate_key": "1:combat", "theme_id": "combat"},
            {"candidate_key": "1:combat", "theme_id": "combat"},
        ],
    }

    with pytest.raises(ValidationError, match="candidate keys must be unique"):
        ThemeMergeResult.model_validate(result_data)
