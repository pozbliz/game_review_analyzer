"""Evidence Filter query contract tests."""

import pytest
from pydantic import ValidationError

from game_review_analyzer.interfaces.http.reports import EvidenceFilterQuery


def test_evidence_filter_query_defaults_to_no_restrictions() -> None:
    assert EvidenceFilterQuery().model_dump() == {
        "recommendation": "all",
        "steam_purchase": None,
        "received_for_free": None,
        "written_during_early_access": None,
        "playtime_basis": "at_review",
        "minimum_playtime_minutes": None,
        "maximum_playtime_minutes": None,
        "review_created_from": None,
        "review_created_to": None,
    }


def test_evidence_filter_query_accepts_approved_scope_controls() -> None:
    query = EvidenceFilterQuery(
        recommendation="recommended",
        steam_purchase=True,
        received_for_free=False,
        written_during_early_access=False,
        playtime_basis="current",
        minimum_playtime_minutes=120,
        maximum_playtime_minutes=600,
        review_created_from=1_700_000_000,
        review_created_to=1_710_000_000,
    )

    assert query.model_dump() == {
        "recommendation": "recommended",
        "steam_purchase": True,
        "received_for_free": False,
        "written_during_early_access": False,
        "playtime_basis": "current",
        "minimum_playtime_minutes": 120,
        "maximum_playtime_minutes": 600,
        "review_created_from": 1_700_000_000,
        "review_created_to": 1_710_000_000,
    }


@pytest.mark.parametrize(
    "values",
    [
        {"minimum_playtime_minutes": 2, "maximum_playtime_minutes": 1},
        {"review_created_from": 2, "review_created_to": 1},
        {"minimum_playtime_minutes": -1},
        {"recommendation": "mixed"},
        {"unknown": True},
    ],
)
def test_evidence_filter_query_rejects_invalid_values(
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        EvidenceFilterQuery(**values)
