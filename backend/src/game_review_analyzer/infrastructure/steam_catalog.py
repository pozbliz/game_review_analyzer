"""Steam keyed catalog and best-effort unkeyed search adapters."""

from collections.abc import Callable, Iterator
import json
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from game_review_analyzer.domain.game_catalog import (
    CatalogGame,
    CatalogPage,
    GameSearchResult,
)


class SteamCatalogUnavailable(Exception):
    """Signal that a Steam catalog or fallback request can be retried later."""


class SteamCatalogAdapter:
    """Read the documented paginated IStoreService catalog with a protected key."""

    def __init__(
        self,
        open_url: Callable[..., Any] = urlopen,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._open_url = open_url
        self._timeout_seconds = timeout_seconds

    def iter_pages(
        self, api_key: str, if_modified_since: int
    ) -> Iterator[CatalogPage]:
        """Yield normalized game pages until Steam declares synchronization complete."""

        last_app_id: int = 0
        while True:
            input_payload: dict[str, int | bool] = {
                "if_modified_since": if_modified_since,
                "include_games": True,
                "last_appid": last_app_id,
                "max_results": 50_000,
            }
            query: str = urlencode(
                {"input_json": json.dumps(input_payload, separators=(",", ":"))}
            )
            request = Request(
                f"https://api.steampowered.com/IStoreService/GetAppList/v1/?{query}",
                headers={
                    "User-Agent": "GameReviewAnalyzer/0.1",
                    "x-webapi-key": api_key,
                },
            )
            try:
                with self._open_url(request, timeout=self._timeout_seconds) as response:
                    payload: Any = json.loads(response.read())
            except (OSError, URLError, json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
                raise SteamCatalogUnavailable("Steam catalog request failed") from error
            response_payload: Any = payload.get("response") if isinstance(payload, dict) else None
            raw_apps: Any = response_payload.get("apps") if isinstance(response_payload, dict) else None
            if not isinstance(raw_apps, list):
                raise SteamCatalogUnavailable("Steam catalog response is malformed")
            games: list[CatalogGame] = []
            for item in raw_apps:
                if not isinstance(item, dict):
                    continue
                try:
                    games.append(
                        CatalogGame(
                            app_id=item["appid"],
                            name=item["name"].strip(),
                            last_modified=item.get("last_modified", 0),
                            price_change_number=item.get("price_change_number", 0),
                        )
                    )
                except (KeyError, AttributeError, ValueError):
                    continue
            yield CatalogPage(games=tuple(games))
            if response_payload.get("have_more_results") is not True:
                return
            next_app_id: Any = response_payload.get("last_appid")
            if not isinstance(next_app_id, int) or next_app_id <= last_app_id:
                raise SteamCatalogUnavailable("Steam catalog cursor is malformed")
            last_app_id = next_app_id


class SteamStoreSearchAdapter:
    """Search Steam's undocumented public store JSON as a replaceable fallback."""

    def __init__(
        self,
        open_url: Callable[..., Any] = urlopen,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._open_url = open_url
        self._timeout_seconds = timeout_seconds

    def search(self, query: str, country_code: str) -> tuple[GameSearchResult, ...]:
        """Return safe normalized fallback matches or an empty result on bad items."""

        request = Request(
            "https://store.steampowered.com/api/storesearch/?"
            + urlencode({"term": query, "l": "english", "cc": country_code}),
            headers={"User-Agent": "GameReviewAnalyzer/0.1"},
        )
        try:
            with self._open_url(request, timeout=self._timeout_seconds) as response:
                payload: Any = json.loads(response.read())
        except (OSError, URLError, json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
            raise SteamCatalogUnavailable("Steam fallback search failed") from error
        items: Any = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise SteamCatalogUnavailable("Steam fallback search response is malformed")
        results: list[GameSearchResult] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            image_url: str | None = safe_steam_image_url(item.get("tiny_image"))
            try:
                results.append(
                    GameSearchResult(
                        app_id=item["id"],
                        title=item["name"].strip(),
                        capsule_image_url=image_url,
                        source="fallback",
                    )
                )
            except (KeyError, AttributeError, ValueError):
                continue
        return tuple(results[:20])


def safe_steam_image_url(value: Any) -> str | None:
    """Allow only HTTPS images hosted on Steam's static asset domain."""

    if not isinstance(value, str) or not value.strip():
        return None
    normalized: str = value.strip()
    parsed = urlparse(normalized)
    hostname: str = parsed.hostname or ""
    return normalized if parsed.scheme == "https" and (
        hostname == "steamstatic.com" or hostname.endswith(".steamstatic.com")
    ) else None
