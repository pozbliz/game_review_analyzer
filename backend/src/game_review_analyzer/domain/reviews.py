"""Normalized Steam review contracts."""

from pydantic import BaseModel, Field


class SteamReview(BaseModel):
    """Represent one eligible Steam review ready for revision persistence."""

    review_id: str = Field(min_length=1)
    language: str
    text: str = Field(min_length=1)
    source_created_at: int = Field(ge=0)
    source_updated_at: int = Field(ge=0)
    recommended: bool
    votes_helpful: int = Field(ge=0)
    votes_funny: int = Field(ge=0)
    weighted_vote_score: float = Field(ge=0)
    steam_purchase: bool
    received_for_free: bool
    written_during_early_access: bool
    playtime_forever_minutes: int = Field(ge=0)
    playtime_at_review_minutes: int | None = Field(ge=0)
