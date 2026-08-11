"""Best-effort Steam storefront metadata retrieval."""

from collections.abc import Callable
import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from game_review_analyzer.domain.steam_metadata import MissingField, SteamMetadata


class SteamGameNotFound(Exception):
    """Signal that callers should present the requested AppID as unavailable."""


class SteamMetadataMalformed(Exception):
    """Signal that callers should reject an unusable Steam metadata response."""


class SteamMetadataUnavailable(Exception):
    """Signal that callers may retry a failed Steam metadata request later."""


class SteamStoreMetadataAdapter:
    """Fetch and normalize one AppID through Steam's public storefront response."""

    def __init__(
        self,
        open_url: Callable[..., Any] = urlopen,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._open_url = open_url
        self._timeout_seconds = timeout_seconds

    def fetch(self, app_id: int) -> SteamMetadata:
        """Return normalized identity data or a specific source failure."""

        if app_id <= 0:
            raise ValueError("AppID must be a positive integer")

        request = Request(
            f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=english",
            headers={"User-Agent": "GameReviewAnalyzer/0.1"},
        )
        try:
            with self._open_url(request, self._timeout_seconds) as response:
                payload: Any = json.loads(response.read())
        except (OSError, URLError) as error:
            raise SteamMetadataUnavailable("Steam metadata request failed") from error
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
            raise SteamMetadataMalformed("Steam returned invalid JSON") from error

        return self._normalize(app_id, payload)

    @staticmethod
    def _normalize(app_id: int, payload: Any) -> SteamMetadata:
        if not isinstance(payload, dict):
            raise SteamMetadataMalformed("Steam metadata response must be an object")
        result: Any = payload.get(str(app_id))
        if not isinstance(result, dict):
            raise SteamMetadataMalformed("Steam metadata response omitted the AppID result")
        if result.get("success") is False:
            raise SteamGameNotFound(f"Steam AppID {app_id} was not found")
        data: Any = result.get("data")
        if result.get("success") is not True or not isinstance(data, dict):
            raise SteamMetadataMalformed("Steam metadata response omitted game data")

        returned_app_id: Any = data.get("steam_appid")
        title: Any = data.get("name")
        if returned_app_id != app_id or not isinstance(title, str) or not title.strip():
            raise SteamMetadataMalformed("Steam metadata response has invalid identity fields")

        developers_value: Any = data.get("developers")
        developers: tuple[str, ...] | None = None
        if isinstance(developers_value, list) and all(
            isinstance(developer, str) and developer.strip() for developer in developers_value
        ):
            developers = tuple(developers_value) or None

        capsule_image_url: str | None = SteamStoreMetadataAdapter._optional_string(
            data.get("header_image")
        )
        release_value: Any = data.get("release_date")
        release_date: str | None = None
        release_status = "unknown"
        if isinstance(release_value, dict) and isinstance(
            release_value.get("coming_soon"), bool
        ):
            release_date = SteamStoreMetadataAdapter._optional_string(release_value.get("date"))
            release_status = "coming_soon" if release_value["coming_soon"] else "released"

        recommendations: Any = data.get("recommendations")
        review_count: int | None = None
        if isinstance(recommendations, dict):
            total: Any = recommendations.get("total")
            if isinstance(total, int) and total >= 0:
                review_count = total

        missing_fields: frozenset[MissingField] = frozenset(
            field_name
            for field_name, value in (
                ("developers", developers),
                ("capsule_image_url", capsule_image_url),
                ("release_date", release_date),
                ("release_status", None if release_status == "unknown" else release_status),
                ("review_count", review_count),
            )
            if value is None
        )
        try:
            return SteamMetadata(
                app_id=app_id,
                title=title.strip(),
                developers=developers,
                capsule_image_url=capsule_image_url,
                release_date=release_date,
                release_status=release_status,
                review_count=review_count,
                source_status="partial" if missing_fields else "complete",
                missing_fields=missing_fields,
            )
        except ValidationError as error:
            raise SteamMetadataMalformed("Steam metadata could not be normalized") from error

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None
