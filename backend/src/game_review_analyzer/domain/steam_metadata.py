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
        return self
