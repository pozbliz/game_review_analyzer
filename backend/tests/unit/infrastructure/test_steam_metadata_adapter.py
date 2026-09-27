"""Fixture-driven tests for the Steam storefront metadata adapter."""

from io import BytesIO
import json
from pathlib import Path
from urllib.request import Request

import pytest

from game_review_analyzer.infrastructure.steam_metadata import (
    SteamGameNotFound,
    SteamMetadataMalformed,
    SteamStoreMetadataAdapter,
)

FIXTURE_DIRECTORY = Path(__file__).parents[2] / "fixtures" / "steam_metadata"


def adapter_for(name: str, country_code: str = "US") -> SteamStoreMetadataAdapter:
    fixture_bytes = (FIXTURE_DIRECTORY / name).read_bytes()

    def open_fixture(request: Request, *, timeout: float) -> BytesIO:
        if f"/app/1145350/" in request.full_url:
            assert request.full_url.endswith(f"?l=english&cc={country_code}")
            return BytesIO(
                (FIXTURE_DIRECTORY / "rich-store.html").read_bytes()
                if name == "rich.json" else b"<html></html>"
            )
        assert request.full_url.endswith(
            f"appdetails?appids=1145350&l=english&cc={country_code}"
        )
        assert timeout == 10.0
        return BytesIO(fixture_bytes)

    return SteamStoreMetadataAdapter(open_url=open_fixture, country_code=country_code)


def test_adapter_normalizes_complete_metadata() -> None:
    metadata = adapter_for("valid.json").fetch(1145350)

    assert metadata.model_dump(mode="json", exclude={
        "storefront", "storefront_source_status", "storefront_missing_fields"
    }) == {
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
    assert metadata.storefront_source_status == "unavailable"


def test_adapter_reports_partial_metadata_without_failing_preview() -> None:
    metadata = adapter_for("partial.json").fetch(1145350)

    assert metadata.source_status == "partial"
    assert metadata.capsule_image_url is None
    assert metadata.missing_fields == frozenset(
        {"capsule_image_url", "release_date", "release_status", "review_count"}
    )


def test_adapter_accepts_one_result_keyed_differently_when_identity_matches() -> None:
    payload: dict[str, object] = json.loads(
        (FIXTURE_DIRECTORY / "valid.json").read_bytes()
    )
    payload["2950840"] = payload.pop("1145350")

    def open_fixture(request: Request, *, timeout: float) -> BytesIO:
        assert timeout == 10.0
        return BytesIO(
            b"<html></html>"
            if "/app/1145350/" in request.full_url
            else json.dumps(payload).encode()
        )

    metadata = SteamStoreMetadataAdapter(open_url=open_fixture).fetch(1145350)

    assert metadata.app_id == 1145350
    assert metadata.title == "Hades II"


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


def test_adapter_normalizes_regional_storefront_and_sanitizes_content() -> None:
    metadata = adapter_for("rich.json", "JP").fetch(1145350)

    assert metadata.storefront.price is not None
    assert metadata.storefront.price.model_dump() == {
        "country_code": "JP",
        "currency": "JPY",
        "initial_minor": 450000,
        "final_minor": 360000,
        "discount_percent": 20,
        "initial_formatted": "¥ 4,500",
        "final_formatted": "¥ 3,600",
    }
    assert metadata.storefront.about_text == "Battle beyond Master dark sorcery."
    assert "alert" not in metadata.storefront.about_text
    assert metadata.storefront.publishers == ("Supergiant Games",)
    assert metadata.storefront.genres == ("Action", "Indie")
    assert metadata.storefront.tags == ("Action", "Roguelike")
    assert metadata.storefront.dlc_names == ("Hades II Soundtrack",)
    assert metadata.storefront.platforms == ("Windows",)
    feature_names: tuple[str, ...] = tuple(
        feature.name for feature in metadata.storefront.features or ()
    )
    assert feature_names.count("Full controller support") == 1
    assert metadata.storefront.screenshot_urls == (
        "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1145350/ss_1.jpg",
    )
    assert metadata.storefront.trailers[0].video_url.startswith("https://video.akamai.steamstatic.com/")
    assert metadata.storefront_missing_fields == frozenset()
    assert metadata.storefront_source_status == "complete"
