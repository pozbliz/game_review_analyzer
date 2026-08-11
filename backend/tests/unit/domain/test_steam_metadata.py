"""Contract tests for normalized Steam metadata."""

import pytest
from pydantic import ValidationError

from game_review_analyzer.domain.steam_metadata import SteamMetadata


def test_complete_metadata_contract_preserves_identity_fields() -> None:
    metadata = SteamMetadata(
        app_id=1145350,
        title="Hades II",
        developers=("Supergiant Games",),
        capsule_image_url="https://cdn.example.test/header.jpg",
        release_date="6 May, 2024",
        release_status="released",
        review_count=48239,
        source_status="complete",
        missing_fields=frozenset(),
    )

    assert metadata.app_id == 1145350
    assert metadata.source_status == "complete"
    assert metadata.missing_fields == frozenset()


def test_partial_metadata_contract_makes_every_unknown_explicit() -> None:
    missing_fields = frozenset(
        {"capsule_image_url", "release_date", "release_status", "review_count"}
    )

    metadata = SteamMetadata(
        app_id=1145350,
        title="Hades II",
        developers=("Supergiant Games",),
        capsule_image_url=None,
        release_date=None,
        release_status="unknown",
        review_count=None,
        source_status="partial",
        missing_fields=missing_fields,
    )

    assert metadata.missing_fields == missing_fields
    assert metadata.source_status == "partial"


def test_metadata_contract_rejects_unreported_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SteamMetadata(
            app_id=1145350,
            title="Hades II",
            developers=None,
            capsule_image_url=None,
            release_date=None,
            release_status="unknown",
            review_count=None,
            source_status="complete",
            missing_fields=frozenset(),
        )
