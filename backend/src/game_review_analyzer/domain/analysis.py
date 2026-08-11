"""Versioned provider-neutral analysis request and result contracts."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ContractModel(BaseModel):
    """Reject fields outside the declared versioned analysis contract."""

    model_config = ConfigDict(extra="forbid")


class OpinionSentiment(StrEnum):
    """Classify one extracted opinion independently of its source review verdict."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class ThemePolarity(StrEnum):
    """Identify the positive or negative report list containing a Theme."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class ThemeCategory(StrEnum):
    """List the approved shared categories available to design Themes."""

    GAMEPLAY = "Gameplay and mechanics"
    PROGRESSION = "Progression and rewards"
    DIFFICULTY = "Difficulty and balance"
    CONTENT = "Content, variety, and replayability"
    CONTROLS = "Controls, interface, and onboarding"
    NARRATIVE = "Narrative, characters, and world"
    MULTIPLAYER = "Multiplayer and social experience"
    VISUALS_AUDIO = "Visuals and audio"
    ACCESSIBILITY = "Accessibility"
    MONETIZATION = "Monetization and value"
    GAME_SPECIFIC = "Game-specific"


class MechanicSentiment(StrEnum):
    """Classify a review's stance toward a mechanic with opposing Themes."""

    LIKED = "liked"
    DISLIKED = "disliked"
    MIXED = "mixed"


class AnalysisSourceReview(ContractModel):
    """Provide one exact Review Revision to an Analysis Provider."""

    review_revision_id: NonEmptyString
    text: NonEmptyString


class AnalysisRequest(ContractModel):
    """Bind a provider request to one exact, privacy-minimized review scope."""

    schema_version: Literal["1.0"]
    request_id: NonEmptyString
    scope_sha256: Sha256Digest
    app_id: int = Field(gt=0)
    game_title: NonEmptyString
    reviews: tuple[AnalysisSourceReview, ...] = Field(min_length=1)


class OpinionPoint(ContractModel):
    """Represent one exact opinion excerpt extracted from a supplied review."""

    id: NonEmptyString
    review_revision_id: NonEmptyString
    excerpt: NonEmptyString
    sentiment: OpinionSentiment
    subject: NonEmptyString
    supports_theme_id: NonEmptyString | None


class ExtractedOpinionPoint(ContractModel):
    """Represent one exact opinion before cross-batch grouping."""

    id: NonEmptyString
    review_revision_id: NonEmptyString
    excerpt: NonEmptyString
    sentiment: OpinionSentiment
    subject: NonEmptyString


class Theme(ContractModel):
    """Group recurring equivalent Opinion Points into one evidence-backed claim."""

    id: NonEmptyString
    title: NonEmptyString
    summary: NonEmptyString
    polarity: ThemePolarity
    primary_category: ThemeCategory
    related_categories: tuple[ThemeCategory, ...]
    opinion_point_ids: tuple[NonEmptyString, ...] = Field(min_length=1)
    technical: bool
    opposes_theme_id: NonEmptyString | None


class MechanicClassification(ContractModel):
    """Record one review's stance toward a mechanic with opposing Themes."""

    review_revision_id: NonEmptyString
    subject: NonEmptyString
    classification: MechanicSentiment


class AnalysisResult(ContractModel):
    """Carry one provider's complete structured result for a bound request scope."""

    schema_version: Literal["1.0"]
    request_id: NonEmptyString
    scope_sha256: Sha256Digest
    provider: NonEmptyString
    model: NonEmptyString
    completed_review_revision_ids: tuple[NonEmptyString, ...] = Field(min_length=1)
    opinion_points: tuple[OpinionPoint, ...]
    themes: tuple[Theme, ...]
    mechanic_classifications: tuple[MechanicClassification, ...]


class OpinionExtractionResult(ContractModel):
    """Carry validated Opinion Points from one bounded review batch."""

    schema_version: Literal["1.0"]
    request_id: NonEmptyString
    scope_sha256: Sha256Digest
    provider: NonEmptyString
    model: NonEmptyString
    completed_review_revision_ids: tuple[NonEmptyString, ...] = Field(min_length=1)
    opinion_points: tuple[ExtractedOpinionPoint, ...]
