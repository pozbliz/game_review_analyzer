"""Normalized Steam metadata contracts."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

MissingField = Literal[
    "developers",
    "capsule_image_url",
    "release_date",
    "release_status",
    "review_count",
]
StorefrontMissingField = Literal[
    "publishers",
    "genres",
    "short_description",
    "about_text",
    "tags",
    "price",
    "is_free",
    "dlc_app_ids",
    "dlc_names",
    "demo_app_ids",
    "package_names",
    "platforms",
    "supported_languages",
    "age_rating",
    "content_notes",
    "features",
    "screenshot_urls",
    "trailers",
]
ALL_STOREFRONT_FIELDS: frozenset[StorefrontMissingField] = frozenset(
    StorefrontMissingField.__args__
)


class SteamPrice(BaseModel):
    """Preserve Steam's regional price exactly without currency conversion."""

    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    currency: str = Field(min_length=3, max_length=3)
    initial_minor: int = Field(ge=0)
    final_minor: int = Field(ge=0)
    discount_percent: int = Field(ge=0, le=100)
    initial_formatted: str = Field(min_length=1)
    final_formatted: str = Field(min_length=1)


class SteamFeature(BaseModel):
    """Describe one textual Steam feature with an explicit support state."""

    name: str = Field(min_length=1)
    group: Literal["Play modes", "Input", "Steam features", "Platforms and accessibility"]
    state: Literal["supported", "partial", "not_supported", "unknown"]


class SteamTrailer(BaseModel):
    """Reference one Steam-hosted trailer that requires explicit navigation."""

    name: str = Field(min_length=1)
    thumbnail_url: str
    video_url: str


class SteamStorefront(BaseModel):
    """Hold normalized optional storefront facts and safe Steam media references."""

    publishers: tuple[str, ...] | None = None
    genres: tuple[str, ...] | None = None
    short_description: str | None = None
    about_text: str | None = None
    tags: tuple[str, ...] | None = None
    price: SteamPrice | None = None
    is_free: bool | None = None
    dlc_app_ids: tuple[int, ...] | None = None
    dlc_names: tuple[str, ...] | None = None
    demo_app_ids: tuple[int, ...] | None = None
    package_names: tuple[str, ...] | None = None
    platforms: tuple[str, ...] | None = None
    supported_languages: str | None = None
    age_rating: str | None = None
    content_notes: str | None = None
    features: tuple[SteamFeature, ...] | None = None
    screenshot_urls: tuple[str, ...] | None = None
    trailers: tuple[SteamTrailer, ...] | None = None


class SteamMetadata(BaseModel):
    """Represent a validated game identity preview returned by a Steam adapter."""

    app_id: int = Field(gt=0)
    title: str = Field(min_length=1)
    developers: tuple[str, ...] | None
    capsule_image_url: str | None
    release_date: str | None
    release_status: Literal["released", "coming_soon", "unknown"]
    review_count: int | None = Field(ge=0)
    source_status: Literal["complete", "partial"]
    missing_fields: frozenset[MissingField]
    storefront: SteamStorefront = Field(default_factory=SteamStorefront)
    storefront_source_status: Literal["complete", "partial", "unavailable"] = "unavailable"
    storefront_missing_fields: frozenset[StorefrontMissingField] = ALL_STOREFRONT_FIELDS

    @model_validator(mode="after")
    def validate_unknown_fields(self) -> Self:
        """Require the status fields to describe every unavailable value exactly."""

        unknown_fields: set[str] = {
            field_name
            for field_name in (
                "developers",
                "capsule_image_url",
                "release_date",
                "review_count",
            )
            if getattr(self, field_name) is None
        }
        if self.release_status == "unknown":
            unknown_fields.add("release_status")

        if unknown_fields != set(self.missing_fields):
            raise ValueError("missing_fields must identify every unknown field")
        expected_status = "partial" if unknown_fields else "complete"
        if self.source_status != expected_status:
            raise ValueError(f"source_status must be {expected_status}")
        missing_storefront: set[str] = {
            field_name
            for field_name in ALL_STOREFRONT_FIELDS
            if getattr(self.storefront, field_name) is None
        }
        if missing_storefront != set(self.storefront_missing_fields):
            raise ValueError(
                "storefront_missing_fields must identify every unavailable storefront field"
            )
        expected_storefront_status: str = (
            "unavailable"
            if len(missing_storefront) == len(ALL_STOREFRONT_FIELDS)
            else "partial" if missing_storefront else "complete"
        )
        if self.storefront_source_status != expected_storefront_status:
            raise ValueError(
                f"storefront_source_status must be {expected_storefront_status}"
            )
        return self
