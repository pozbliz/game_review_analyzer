"""Versioned provider-neutral analysis request and result contracts."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonNegativePosition = Annotated[int, Field(strict=True, ge=0)]
ANALYSIS_CONTRACT_VERSION = "3.1"


class ContractModel(BaseModel):
    """Reject fields outside the declared versioned analysis contract."""

    model_config = ConfigDict(extra="forbid")


class ThemePolarity(StrEnum):
    """Identify the positive or negative report list containing a Theme."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class AnalysisSourceReview(ContractModel):
    """Provide one exact Review Revision to an Analysis Provider."""

    review_revision_id: NonEmptyString
    text: NonEmptyString


class ThemeAnalysisRequest(ContractModel):
    """Bind a Version 3 Theme candidate request to one exact review scope."""

    schema_version: Literal["3.1"]
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


class ThemeCandidateOutput(ContractModel):
    """Return one semantic Theme candidate from a provider map call."""

    title: NonEmptyString
    summary: NonEmptyString
    polarity: ThemePolarity
    supporting_review_positions: tuple[NonNegativePosition, ...] = Field(min_length=1)


class ThemeAnalysisOutput(ContractModel):
    """Return only semantic Theme candidates from one provider map call."""

    themes: tuple[ThemeCandidateOutput, ...]


class ThemeAnalysisResult(ContractModel):
    """Return validated Theme candidates for one complete review batch."""

    schema_version: Literal["3.1"]
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


class ThemeMergeTheme(ContractModel):
    """Define one merged or established Theme."""

    theme_id: NonEmptyString
    title: NonEmptyString
    summary: NonEmptyString
    polarity: ThemePolarity


class ThemeMergeRequest(ContractModel):
    """Bind one merge call to the complete set of mapped candidates."""

    schema_version: Literal["3.1"]
    request_id: NonEmptyString
    scope_sha256: Sha256Digest
    app_id: int = Field(gt=0)
    game_title: NonEmptyString
    established_themes: tuple[ThemeMergeTheme, ...] = ()
    candidates: tuple[ThemeMergeCandidate, ...] = Field(min_length=1)


class ThemeMergeAssignment(ContractModel):
    """Assign one source candidate to a merged Theme or discard it."""

    candidate_key: NonEmptyString
    theme_id: NonEmptyString | None


class ThemeMergeThemeOutput(ContractModel):
    """Return one semantic Theme definition from a provider merge call."""

    title: NonEmptyString
    summary: NonEmptyString
    polarity: ThemePolarity


class ThemeMergeAssignmentOutput(ContractModel):
    """Assign one ordered candidate to an established or new Theme position."""

    established_theme_position: NonNegativePosition | None
    new_theme_position: NonNegativePosition | None

    @model_validator(mode="after")
    def require_one_target(self) -> "ThemeMergeAssignmentOutput":
        """Allow one target or discard, but never two targets."""

        if (
            self.established_theme_position is not None
            and self.new_theme_position is not None
        ):
            raise ValueError("Merge assignment cannot target two Themes")
        return self


class ThemeMergeOutput(ContractModel):
    """Return semantic new Themes and ordered candidate assignments."""

    new_themes: tuple[ThemeMergeThemeOutput, ...]
    assignments: tuple[ThemeMergeAssignmentOutput, ...]


class ThemeMergeResult(ContractModel):
    """Return Themes and one Theme-or-discard assignment per source candidate."""

    schema_version: Literal["3.1"]
    request_id: NonEmptyString
    scope_sha256: Sha256Digest
    provider: NonEmptyString
    model: NonEmptyString
    themes: tuple[ThemeMergeTheme, ...]
    assignments: tuple[ThemeMergeAssignment, ...]

    @model_validator(mode="after")
    def require_unique_identifiers(self) -> "ThemeMergeResult":
        """Reject repeated Themes and assignments to missing Themes."""

        theme_ids: tuple[str, ...] = tuple(theme.theme_id for theme in self.themes)
        if len(theme_ids) != len(set(theme_ids)):
            raise ValueError("Merged Theme identifiers must be unique")
        candidate_keys: tuple[str, ...] = tuple(
            assignment.candidate_key for assignment in self.assignments
        )
        if len(candidate_keys) != len(set(candidate_keys)):
            raise ValueError("Merge assignment candidate keys must be unique")
        assigned_theme_ids: set[str] = {
            assignment.theme_id
            for assignment in self.assignments
            if assignment.theme_id is not None
        }
        if not assigned_theme_ids <= set(theme_ids):
            raise ValueError("Assignments must reference returned Themes")
        return self
