"""Best-effort Steam storefront metadata retrieval."""

from collections.abc import Callable
from html import unescape
from html.parser import HTMLParser
import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from game_review_analyzer.domain.steam_metadata import (
    ALL_STOREFRONT_FIELDS,
    MissingField,
    SteamFeature,
    SteamMetadata,
    SteamPrice,
    SteamStorefront,
    SteamTrailer,
    StorefrontMissingField,
)
from game_review_analyzer.infrastructure.steam_catalog import safe_steam_image_url


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
        country_code: str = "US",
    ) -> None:
        self._open_url = open_url
        self._timeout_seconds = timeout_seconds
        self._country_code = country_code.upper()

    def fetch(self, app_id: int) -> SteamMetadata:
        """Return normalized identity data or a specific source failure."""

        if app_id <= 0:
            raise ValueError("AppID must be a positive integer")

        request = Request(
            f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=english&cc={self._country_code}",
            headers={"User-Agent": "GameReviewAnalyzer/0.1"},
        )
        try:
            with self._open_url(request, timeout=self._timeout_seconds) as response:
                payload: Any = json.loads(response.read())
        except (OSError, URLError) as error:
            raise SteamMetadataUnavailable("Steam metadata request failed") from error
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
            raise SteamMetadataMalformed("Steam returned invalid JSON") from error

        tags, dlc_names = self._fetch_store_page_details(app_id)
        return self._normalize(
            app_id, payload, self._country_code, tags=tags, dlc_names=dlc_names
        )

    def _fetch_store_page_details(
        self, app_id: int
    ) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None]:
        """Best-effort parse visible tags and DLC names from one Steam store page."""

        request = Request(
            f"https://store.steampowered.com/app/{app_id}/?l=english&cc={self._country_code}",
            headers={"User-Agent": "GameReviewAnalyzer/0.1"},
        )
        try:
            with self._open_url(request, timeout=self._timeout_seconds) as response:
                document: str = response.read().decode("utf-8")
        except (OSError, URLError, UnicodeDecodeError, AttributeError):
            return None, None
        parser = StorePageParser()
        parser.feed(document)
        return tuple(dict.fromkeys(parser.tags)) or None, tuple(dict.fromkeys(parser.dlc_names)) or None

    @staticmethod
    def _normalize(
        app_id: int,
        payload: Any,
        country_code: str = "US",
        tags: tuple[str, ...] | None = None,
        dlc_names: tuple[str, ...] | None = None,
    ) -> SteamMetadata:
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

        capsule_image_url: str | None = SteamStoreMetadataAdapter._optional_steam_image_url(
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
        storefront: SteamStorefront = SteamStoreMetadataAdapter._normalize_storefront(
            data, country_code, tags, dlc_names
        )
        storefront_missing_fields: frozenset[StorefrontMissingField] = frozenset(
            field_name
            for field_name in ALL_STOREFRONT_FIELDS
            if getattr(storefront, field_name) is None
        )
        storefront_source_status = (
            "unavailable"
            if len(storefront_missing_fields) == len(ALL_STOREFRONT_FIELDS)
            else "partial" if storefront_missing_fields else "complete"
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
                storefront=storefront,
                storefront_source_status=storefront_source_status,
                storefront_missing_fields=storefront_missing_fields,
            )
        except ValidationError as error:
            raise SteamMetadataMalformed("Steam metadata could not be normalized") from error

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _optional_steam_image_url(value: Any) -> str | None:
        return safe_steam_image_url(value)

    @staticmethod
    def _normalize_storefront(
        data: dict[str, Any],
        country_code: str,
        tags: tuple[str, ...] | None,
        dlc_names: tuple[str, ...] | None,
    ) -> SteamStorefront:
        """Normalize optional store facts while reducing markup to plain text."""

        publishers: tuple[str, ...] | None = string_tuple(data.get("publishers"))
        genres: tuple[str, ...] | None = described_tuple(data.get("genres"))
        short_description: str | None = html_to_text(data.get("short_description"))
        about_text: str | None = html_to_text(data.get("about_the_game"))
        price: SteamPrice | None = normalize_price(data.get("price_overview"), country_code)
        dlc_app_ids: tuple[int, ...] | None = positive_id_tuple(data.get("dlc"))
        demos: Any = data.get("demos")
        demo_app_ids: tuple[int, ...] | None = positive_id_tuple(
            [item.get("appid") for item in demos if isinstance(item, dict)]
            if isinstance(demos, list) else None
        )
        package_names: tuple[str, ...] | None = normalize_package_names(
            data.get("package_groups")
        )
        platforms_value: Any = data.get("platforms")
        platforms: tuple[str, ...] | None = None
        platform_features: list[SteamFeature] = []
        if isinstance(platforms_value, dict):
            platform_names: dict[str, str] = {
                "windows": "Windows", "mac": "macOS", "linux": "Linux"
            }
            platforms = tuple(
                label for key, label in platform_names.items()
                if platforms_value.get(key) is True
            )
            platform_features = [
                SteamFeature(
                    name=label,
                    group="Platforms and accessibility",
                    state="supported" if platforms_value.get(key) is True else "not_supported",
                )
                for key, label in platform_names.items()
                if isinstance(platforms_value.get(key), bool)
            ]
        category_features: tuple[SteamFeature, ...] = normalize_features(
            data.get("categories")
        )
        screenshots_value: Any = data.get("screenshots")
        screenshot_urls: tuple[str, ...] | None = None
        if isinstance(screenshots_value, list):
            screenshot_urls = tuple(
                url for item in screenshots_value if isinstance(item, dict)
                if (url := safe_steam_image_url(item.get("path_full"))) is not None
            ) or None
        trailers: tuple[SteamTrailer, ...] | None = normalize_trailers(data.get("movies"))
        is_free: bool | None = data.get("is_free") if isinstance(data.get("is_free"), bool) else None
        return SteamStorefront(
            publishers=publishers,
            genres=genres,
            short_description=short_description,
            about_text=about_text,
            tags=tags,
            price=price,
            is_free=is_free,
            dlc_app_ids=dlc_app_ids,
            dlc_names=dlc_names,
            demo_app_ids=demo_app_ids,
            package_names=package_names,
            platforms=platforms,
            supported_languages=html_to_text(data.get("supported_languages")),
            age_rating=SteamStoreMetadataAdapter._optional_string(data.get("required_age")),
            content_notes=html_to_text(
                data.get("content_descriptors", {}).get("notes")
                if isinstance(data.get("content_descriptors"), dict) else None
            ),
            features=tuple(platform_features) + category_features or None,
            screenshot_urls=screenshot_urls,
            trailers=trailers,
        )


class PlainTextParser(HTMLParser):
    """Reduce untrusted storefront markup to readable text and drop executable blocks."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth: int = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.parts.append(data.strip())


class StorePageParser(HTMLParser):
    """Extract only visible tag labels and DLC names from best-effort store HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.dlc_names: list[str] = []
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes: set[str] = set(dict(attrs).get("class", "").split())
        if tag == "a" and "app_tag" in classes:
            self._capture = "tag"
        elif tag == "div" and "game_area_dlc_name" in classes:
            self._capture = "dlc"

    def handle_endtag(self, tag: str) -> None:
        if (tag == "a" and self._capture == "tag") or (
            tag == "div" and self._capture == "dlc"
        ):
            self._capture = None

    def handle_data(self, data: str) -> None:
        value: str = data.strip()
        if not value:
            return
        if self._capture == "tag":
            self.tags.append(value)
        elif self._capture == "dlc":
            self.dlc_names.append(value)


def html_to_text(value: Any) -> str | None:
    """Return normalized plain text from optional untrusted storefront markup."""

    if not isinstance(value, str) or not value.strip():
        return None
    parser = PlainTextParser()
    parser.feed(unescape(value))
    text: str = " ".join(parser.parts).strip()
    return text or None


def string_tuple(value: Any) -> tuple[str, ...] | None:
    """Normalize a non-empty string list."""

    if not isinstance(value, list):
        return None
    items: tuple[str, ...] = tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )
    return items or None


def described_tuple(value: Any) -> tuple[str, ...] | None:
    """Normalize Steam objects containing display descriptions."""

    if not isinstance(value, list):
        return None
    return string_tuple([
        item.get("description") for item in value if isinstance(item, dict)
    ])


def positive_id_tuple(value: Any) -> tuple[int, ...] | None:
    """Normalize a list of positive Steam identifiers."""

    if not isinstance(value, list):
        return None
    identifiers: tuple[int, ...] = tuple(
        item for item in value if isinstance(item, int) and item > 0
    )
    return identifiers or None


def normalize_price(value: Any, country_code: str) -> SteamPrice | None:
    """Preserve a complete regional Steam price without conversion."""

    if not isinstance(value, dict):
        return None
    try:
        return SteamPrice(
            country_code=country_code,
            currency=value["currency"],
            initial_minor=value["initial"],
            final_minor=value["final"],
            discount_percent=value["discount_percent"],
            initial_formatted=value["initial_formatted"],
            final_formatted=value["final_formatted"],
        )
    except (KeyError, ValueError):
        return None


def normalize_package_names(value: Any) -> tuple[str, ...] | None:
    """Flatten safe package option text from Steam package groups."""

    if not isinstance(value, list):
        return None
    names: list[str] = []
    for group in value:
        subs: Any = group.get("subs") if isinstance(group, dict) else None
        if isinstance(subs, list):
            names.extend(
                text for item in subs if isinstance(item, dict)
                if (text := html_to_text(item.get("option_text"))) is not None
            )
    return tuple(names) or None


def normalize_features(value: Any) -> tuple[SteamFeature, ...]:
    """Group returned Steam category descriptions without inventing absent support."""

    descriptions: tuple[str, ...] = tuple(dict.fromkeys(described_tuple(value) or ()))
    features: list[SteamFeature] = []
    for description in descriptions:
        lowered: str = description.lower()
        group = (
            "Input" if "controller" in lowered
            else "Play modes" if any(word in lowered for word in ("player", "co-op", "pvp"))
            else "Steam features"
        )
        features.append(SteamFeature(name=description, group=group, state="supported"))
    return tuple(features)


def normalize_trailers(value: Any) -> tuple[SteamTrailer, ...] | None:
    """Keep only complete Steam-hosted trailer references."""

    if not isinstance(value, list):
        return None
    trailers: list[SteamTrailer] = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("mp4"), dict):
            continue
        name: Any = item.get("name")
        thumbnail_url: str | None = safe_steam_image_url(item.get("thumbnail"))
        video_url: str | None = safe_steam_image_url(item["mp4"].get("max"))
        if isinstance(name, str) and name.strip() and thumbnail_url and video_url:
            trailers.append(
                SteamTrailer(
                    name=name.strip(),
                    thumbnail_url=thumbnail_url,
                    video_url=video_url,
                )
            )
    return tuple(trailers) or None
