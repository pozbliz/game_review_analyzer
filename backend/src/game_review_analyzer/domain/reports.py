"""Immutable report snapshot and deterministic metric value contracts."""

from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from game_review_analyzer.domain.analysis import (
    AnalysisResult,
    ContractModel,
    NonEmptyString,
    ThemeCategory,
    ThemePolarity,
)
from game_review_analyzer.domain.steam_metadata import SteamMetadata


class ReportContractModel(ContractModel):
    """Reject undeclared fields and prevent mutation of report values."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ThemeMetricPolicy(ReportContractModel):
    """Supply explicit thresholds and headline caps for one calculation."""

    minimum_support_count: int = Field(ge=1)
    minimum_support_percentage: float = Field(ge=0, le=100)
    technical_minimum_support_count: int = Field(ge=1)
    technical_minimum_support_percentage: float = Field(ge=0, le=100)
    maximum_headlines_per_polarity: int = Field(default=10, ge=1)


class ThemeMetric(ReportContractModel):
    """Expose one Theme's deterministic support and taxonomy fields."""

    theme_id: NonEmptyString
    polarity: ThemePolarity
    primary_category: ThemeCategory
    related_categories: tuple[ThemeCategory, ...]
    technical: bool
    support_count: int = Field(ge=0)
    support_percentage: float = Field(ge=0, le=100)


class MixedReceptionMetric(ReportContractModel):
    """Describe review-level reception for one opposing Theme pair."""

    positive_theme_id: NonEmptyString
    negative_theme_id: NonEmptyString
    liked_count: int = Field(ge=0)
    disliked_count: int = Field(ge=0)
    mixed_count: int = Field(ge=0)
    opinionated_review_count: int = Field(gt=0)
    mentioned_review_count: int = Field(gt=0)
    scope_review_count: int = Field(gt=0)
    liked_percentage: float = Field(ge=0, le=100)
    disliked_percentage: float = Field(ge=0, le=100)
    mixed_percentage: float = Field(ge=0, le=100)
    mentioned_percentage: float = Field(ge=0, le=100)


class ThemeMetrics(ReportContractModel):
    """Return all metrics plus filtered report presentation groups."""

    all_themes: tuple[ThemeMetric, ...]
    positive_headlines: tuple[ThemeMetric, ...]
    negative_headlines: tuple[ThemeMetric, ...]
    technical_themes: tuple[ThemeMetric, ...]
    mixed_reception: tuple[MixedReceptionMetric, ...]


class ReportVersion(ReportContractModel):
    """Preserve one complete report result and its exact immutable scope."""

    schema_version: Literal["2.0"]
    report_version_id: NonEmptyString
    app_id: int = Field(gt=0)
    metadata_snapshot: SteamMetadata
    review_revision_ids: tuple[int, ...] = Field(min_length=1)
    analysis_result: AnalysisResult
    metric_policy: ThemeMetricPolicy
    theme_metrics: ThemeMetrics
    thresholds_calibrated: bool

    @field_validator("review_revision_ids")
    @classmethod
    def require_unique_revision_ids(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        """Reject ambiguous report scopes with repeated Revision identifiers."""

        if len(value) != len(set(value)) or any(identifier <= 0 for identifier in value):
            raise ValueError("Review Revision identifiers must be unique and positive")
        return value

    @model_validator(mode="after")
    def require_matching_metadata(self) -> "ReportVersion":
        """Bind the metadata snapshot to the same game as the report scope."""

        if self.metadata_snapshot.app_id != self.app_id:
            raise ValueError("Report metadata must match the report AppID")
        return self
