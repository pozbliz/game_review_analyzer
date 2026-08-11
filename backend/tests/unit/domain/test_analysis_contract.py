"""Public contract tests for versioned analysis requests and results."""

import pytest
from pydantic import ValidationError

from game_review_analyzer.domain.analysis import AnalysisRequest, AnalysisResult


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
