"""Durable catalog synchronization and local-first search tests."""

from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient

from game_review_analyzer.domain.game_catalog import CatalogGame, CatalogPage, GameSearchResult
from game_review_analyzer.infrastructure.persistence.game_catalog import search_catalog
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings


class CatalogSource:
    """Yield one deterministic catalog page and record incremental inputs."""

    def __init__(self) -> None:
        self.if_modified_since: list[int] = []

    def iter_pages(self, api_key: str, if_modified_since: int) -> Iterator[CatalogPage]:
        assert api_key == "secret-key"
        self.if_modified_since.append(if_modified_since)
        yield CatalogPage(games=(CatalogGame(app_id=1145350, name="Hades II", last_modified=100, price_change_number=2),))


class FallbackSource:
    """Return one deterministic best-effort result and record its region."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def search(self, query: str, country_code: str) -> tuple[GameSearchResult, ...]:
        self.calls.append((query, country_code))
        return (GameSearchResult(app_id=367520, title="Hollow Knight", source="fallback"),)


def test_catalog_sync_is_incremental_and_search_is_local_first(tmp_path: Path) -> None:
    source = CatalogSource()
    fallback = FallbackSource()
    settings = Settings(
        database_path=tmp_path / "app.sqlite3",
        steam_web_api_key="secret-key",
        steam_country_code="JP",
    )

    with TestClient(create_app(settings, catalog_source=source, fallback_search_source=fallback)) as client:
        first_sync = client.post("/api/catalog/sync")
        local = client.get("/api/games/search", params={"q": "hades"})
        remote = client.get("/api/games/search", params={"q": "hollow"})
        second_sync = client.post("/api/catalog/sync")

    assert first_sync.status_code == 200
    assert first_sync.json()["updated_game_count"] == 1
    assert [item["source"] for item in local.json()] == ["catalog"]
    assert fallback.calls == [("hollow", "JP")]
    assert remote.json()[0]["title"] == "Hollow Knight"
    assert source.if_modified_since == [0, first_sync.json()["synced_at"]]
    assert search_catalog(settings.database_path, "hades")[0].title == "Hades II"


def test_catalog_sync_requires_a_configured_key(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(database_path=tmp_path / "app.sqlite3"))) as client:
        response = client.post("/api/catalog/sync")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "steam_key_required"
