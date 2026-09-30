"""Versioned provider-neutral analysis request and result contracts."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
ANALYSIS_CONTRACT_VERSION = "3.0"


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


class ThemeAnalysisRequest(ContractModel):
    """Bind a Version 3 Theme candidate request to one exact review scope."""

    schema_version: Literal["3.0"]
    request_id: NonEmptyString
    scope_sha256: Sha256Digest
    app_id: int = Field(gt=0)
    game_title: NonEmptyString
    reviews: tuple[AnalysisSourceReview, ...] = Field(min_length=1)


class ThemeCandidate(ContractModel):
    """Describe one recurring opinion and its supporting batch reviews."""

    candidate_id: NonEmptyString
    title: NonEmptyString
    summary: NonEmptyString
    polarity: ThemePolarity
    supporting_review_revision_ids: tuple[NonEmptyString, ...] = Field(min_length=1)

    @field_validator("supporting_review_revision_ids")
    @classmethod
    def require_unique_memberships(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Reject repeated support from one review within a candidate."""

        if len(value) != len(set(value)):
            raise ValueError("Theme candidate memberships must be unique")
        return value


class ThemeAnalysisResult(ContractModel):
    """Return validated Theme candidates for one complete review batch."""

    schema_version: Literal["3.0"]
    request_id: NonEmptyString
    scope_sha256: Sha256Digest
    provider: NonEmptyString
    model: NonEmptyString
    completed_review_revision_ids: tuple[NonEmptyString, ...] = Field(min_length=1)
    themes: tuple[ThemeCandidate, ...]

    @model_validator(mode="after")
    def require_valid_identifiers(self) -> "ThemeAnalysisResult":
        """Reject repeated identifiers and memberships outside the completed batch."""

        completed_ids: set[str] = set(self.completed_review_revision_ids)
        if len(completed_ids) != len(self.completed_review_revision_ids):
            raise ValueError("Completed review identifiers must be unique")
        candidate_ids: tuple[str, ...] = tuple(
            candidate.candidate_id for candidate in self.themes
        )
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Theme candidate identifiers must be unique")
        if any(
            not set(candidate.supporting_review_revision_ids) <= completed_ids
            for candidate in self.themes
        ):
            raise ValueError("Theme candidates must reference completed reviews")
        return self


class ThemeMergeCandidate(ContractModel):
    """Identify one validated map candidate for cross-batch merging."""

    candidate_key: NonEmptyString
    title: NonEmptyString
    summary: NonEmptyString
    polarity: ThemePolarity
    supporting_review_revision_ids: tuple[NonEmptyString, ...] = Field(min_length=1)


class ThemeMergeRequest(ContractModel):
    """Bind one merge call to the complete set of mapped candidates."""

    schema_version: Literal["3.0"]
    request_id: NonEmptyString
    scope_sha256: Sha256Digest
    app_id: int = Field(gt=0)
    game_title: NonEmptyString
    candidates: tuple[ThemeMergeCandidate, ...] = Field(min_length=1)


class ThemeMergeTheme(ContractModel):
    """Map source candidates into one merged Theme definition."""

    theme_id: NonEmptyString
    title: NonEmptyString
    summary: NonEmptyString
    polarity: ThemePolarity
    source_candidate_keys: tuple[NonEmptyString, ...] = Field(min_length=1)


class ThemeMergeResult(ContractModel):
    """Return Theme mappings and explicit discards for every source candidate."""

    schema_version: Literal["3.0"]
    request_id: NonEmptyString
    scope_sha256: Sha256Digest
    provider: NonEmptyString
    model: NonEmptyString
    completed_candidate_keys: tuple[NonEmptyString, ...] = Field(min_length=1)
    themes: tuple[ThemeMergeTheme, ...]
    discarded_candidate_keys: tuple[NonEmptyString, ...]

    @model_validator(mode="after")
    def require_unique_identifiers(self) -> "ThemeMergeResult":
        """Reject repeated Theme, completion, mapping, and discard identifiers."""

        completed: tuple[str, ...] = self.completed_candidate_keys
        theme_ids: tuple[str, ...] = tuple(theme.theme_id for theme in self.themes)
        mapped: tuple[str, ...] = tuple(
            key for theme in self.themes for key in theme.source_candidate_keys
        )
        discarded: tuple[str, ...] = self.discarded_candidate_keys
        if len(completed) != len(set(completed)):
            raise ValueError("Completed candidate keys must be unique")
        if len(theme_ids) != len(set(theme_ids)):
            raise ValueError("Merged Theme identifiers must be unique")
        if len(mapped) != len(set(mapped)):
            raise ValueError("Source candidates must map at most once")
        if len(discarded) != len(set(discarded)) or set(mapped) & set(discarded):
            raise ValueError("Discarded candidate keys must be unique and unmapped")
        return self


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
