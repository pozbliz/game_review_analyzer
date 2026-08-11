"""Current Steam catalog and best-effort fallback adapter tests."""

from io import BytesIO
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

from game_review_analyzer.infrastructure.steam_catalog import (
    SteamCatalogAdapter,
    SteamStoreSearchAdapter,
)

FIXTURES = Path(__file__).parents[2] / "fixtures" / "steam_catalog"


def test_keyed_catalog_uses_header_and_documented_pagination() -> None:
    requests: list[Request] = []

    def open_fixture(request: Request, *, timeout: float) -> BytesIO:
        requests.append(request)
        payload = "page_1.json" if len(requests) == 1 else "page_2.json"
        return BytesIO((FIXTURES / payload).read_bytes())

    pages = tuple(
        SteamCatalogAdapter(open_url=open_fixture).iter_pages(
            "secret-key", if_modified_since=50
        )
    )

    assert [game.name for page in pages for game in page.games] == [
        "Hades II", "ELDEN RING", "Hollow Knight"
    ]
    assert len(requests) == 2
    assert all("secret-key" not in request.full_url for request in requests)
    assert all(request.get_header("X-webapi-key") == "secret-key" for request in requests)
    first_input = json.loads(parse_qs(urlparse(requests[0].full_url).query)["input_json"][0])
    second_input = json.loads(parse_qs(urlparse(requests[1].full_url).query)["input_json"][0])
    assert first_input == {
        "if_modified_since": 50,
        "include_games": True,
        "last_appid": 0,
        "max_results": 50000,
    }
    assert second_input["last_appid"] == 1245620


def test_unkeyed_fallback_normalizes_only_safe_steam_results() -> None:
    def open_fixture(request: Request, *, timeout: float) -> BytesIO:
        query = parse_qs(urlparse(request.full_url).query)
        assert query == {"term": ["Hades 2"], "l": ["english"], "cc": ["JP"]}
        return BytesIO((FIXTURES / "fallback.json").read_bytes())

    results = SteamStoreSearchAdapter(open_url=open_fixture).search("Hades 2", "JP")

    assert [result.model_dump(mode="json") for result in results] == [{
        "app_id": 1145350,
        "title": "Hades II",
        "capsule_image_url": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1145350/capsule_sm_120.jpg",
        "source": "fallback",
    }]
