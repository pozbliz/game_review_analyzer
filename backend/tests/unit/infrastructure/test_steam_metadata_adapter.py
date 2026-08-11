"""Fixture-driven tests for the Steam storefront metadata adapter."""

from io import BytesIO
from pathlib import Path
from urllib.request import Request

import pytest

from game_review_analyzer.infrastructure.steam_metadata import (
    SteamGameNotFound,
    SteamMetadataMalformed,
    SteamStoreMetadataAdapter,
)

FIXTURE_DIRECTORY = Path(__file__).parents[2] / "fixtures" / "steam_metadata"


def adapter_for(name: str) -> SteamStoreMetadataAdapter:
    fixture_bytes = (FIXTURE_DIRECTORY / name).read_bytes()

    def open_fixture(request: Request, *, timeout: float) -> BytesIO:
        assert request.full_url.endswith("appdetails?appids=1145350&l=english")
        assert timeout == 10.0
        return BytesIO(fixture_bytes)

    return SteamStoreMetadataAdapter(open_url=open_fixture)


def test_adapter_normalizes_complete_metadata() -> None:
    metadata = adapter_for("valid.json").fetch(1145350)

    assert metadata.model_dump(mode="json") == {
        "app_id": 1145350,
        "title": "Hades II",
        "developers": ["Supergiant Games"],
        "capsule_image_url": "https://cdn.akamai.steamstatic.com/steam/apps/1145350/header.jpg",
        "release_date": "6 May, 2024",
        "release_status": "released",
        "review_count": 48239,
        "source_status": "complete",
        "missing_fields": [],
    }


def test_adapter_reports_partial_metadata_without_failing_preview() -> None:
    metadata = adapter_for("partial.json").fetch(1145350)

    assert metadata.source_status == "partial"
    assert metadata.capsule_image_url is None
    assert metadata.missing_fields == frozenset(
        {"capsule_image_url", "release_date", "release_status", "review_count"}
    )


def test_adapter_distinguishes_missing_and_malformed_games() -> None:
    with pytest.raises(SteamGameNotFound):
        adapter_for("missing.json").fetch(1145350)

    with pytest.raises(SteamMetadataMalformed):
        adapter_for("malformed.json").fetch(1145350)


def test_adapter_rejects_invalid_app_id_before_requesting_steam() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        adapter_for("invalid.json").fetch(0)


def test_adapter_discards_non_steam_capsule_urls() -> None:
    fixture_bytes = (FIXTURE_DIRECTORY / "valid.json").read_bytes().replace(
        b"https://cdn.akamai.steamstatic.com/steam/apps/1145350/header.jpg",
        b"javascript:alert(1)",
    )

    def open_fixture(_: Request, *, timeout: float) -> BytesIO:
        assert timeout == 10.0
        return BytesIO(fixture_bytes)

    metadata = SteamStoreMetadataAdapter(open_url=open_fixture).fetch(1145350)

    assert metadata.capsule_image_url is None
    assert "capsule_image_url" in metadata.missing_fields
