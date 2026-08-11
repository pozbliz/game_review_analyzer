"""Normalized Steam game-catalog contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class CatalogGame(BaseModel):
    """Represent one keyed Steam catalog entry suitable for local search."""

    app_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    last_modified: int = Field(ge=0)
    price_change_number: int = Field(ge=0)


class CatalogPage(BaseModel):
    """Carry one normalized page from Steam's current catalog endpoint."""

    games: tuple[CatalogGame, ...]


class GameSearchResult(BaseModel):
    """Present a safe game match from either the local catalog or fallback source."""

    app_id: int = Field(gt=0)
    title: str = Field(min_length=1)
    capsule_image_url: str | None = None
    source: Literal["catalog", "fallback"]


class CatalogSyncResult(BaseModel):
    """Summarize one completed incremental keyed-catalog synchronization."""

    updated_game_count: int = Field(ge=0)
    synced_at: int = Field(ge=0)
