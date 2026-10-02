"""HTTP contract tests for direct-AppID game preview."""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.game_datasets import load_game_dataset
from game_review_analyzer.infrastructure.steam_metadata import (
    SteamGameNotFound,
    SteamMetadataMalformed,
    SteamMetadataUnavailable,
)
from game_review_analyzer.infrastructure.steam_reviews import ReviewLanguageCount
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings


class StubMetadataSource:
    """Return one configured result or failure through the adapter seam."""

    def __init__(
        self,
        result: SteamMetadata | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.requested_app_ids: list[int] = []

    def fetch(self, app_id: int) -> SteamMetadata:
        self.requested_app_ids.append(app_id)
        if self.error:
            raise self.error
        assert self.result is not None
        return self.result


class StubReviewLanguageSource:
    """Return deterministic Steam review totals by language."""

    def fetch(self, app_id: int) -> tuple[ReviewLanguageCount, ...]:
        assert app_id == 1145350
        return (
            ReviewLanguageCount(language="English", review_count=3_786),
            ReviewLanguageCount(language="German", review_count=2_410),
        )


def partial_metadata() -> SteamMetadata:
    missing_fields = frozenset(
        {"capsule_image_url", "release_date", "release_status", "review_count"}
    )
    return SteamMetadata(
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


def test_preview_validates_persists_and_returns_partial_metadata(tmp_path: Path) -> None:
    database_path = tmp_path / "app.sqlite3"
    source = StubMetadataSource(result=partial_metadata())
    settings = Settings(database_path=database_path)

    with TestClient(create_app(settings, metadata_source=source)) as client:
        response = client.get("/api/games/preview", params={"appid": "1145350"})

    assert response.status_code == 200
    assert response.json()["source_status"] == "partial"
    assert response.json()["capsule_image_url"] is None
    assert source.requested_app_ids == [1145350]
    assert load_game_dataset(database_path, 1145350) == partial_metadata()


def test_review_language_totals_are_loaded_on_demand(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    source = StubMetadataSource(result=partial_metadata())

    with TestClient(create_app(
        Settings(database_path=database_path),
        metadata_source=source,
        review_language_source=StubReviewLanguageSource(),
    )) as client:
        client.get("/api/games/preview", params={"appid": "1145350"})
        response = client.get("/api/games/1145350/review-languages")

    assert response.status_code == 200
    assert response.json() == [
        {"language": "English", "review_count": 3_786},
        {"language": "German", "review_count": 2_410},
    ]


@pytest.mark.parametrize("app_id", ["abc", "0", "-1", "01"])
def test_preview_rejects_invalid_app_ids_before_requesting_steam(
    tmp_path: Path,
    app_id: str,
) -> None:
    source = StubMetadataSource(result=partial_metadata())
    settings = Settings(database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings, metadata_source=source)) as client:
        response = client.get("/api/games/preview", params={"appid": app_id})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_app_id"
    assert source.requested_app_ids == []


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (SteamGameNotFound(), 404, "game_not_found"),
        (SteamMetadataMalformed(), 502, "invalid_steam_response"),
        (SteamMetadataUnavailable(), 503, "steam_unavailable"),
    ],
)
def test_preview_preserves_specific_source_failures(
    tmp_path: Path,
    error: Exception,
    status_code: int,
    code: str,
) -> None:
    settings = Settings(database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings, metadata_source=StubMetadataSource(error=error))) as client:
        response = client.get("/api/games/preview", params={"appid": "1145350"})

    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == code
