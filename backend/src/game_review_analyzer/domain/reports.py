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


class ThemeDefinition(ReportContractModel):
    """Store one stable aggregate Theme definition without review evidence."""

    theme_id: NonEmptyString
    title: NonEmptyString
    summary: NonEmptyString
    polarity: ThemePolarity


class ThemeMembership(ReportContractModel):
    """Link one aggregate Theme to one local Review Revision."""

    theme_id: NonEmptyString
    review_revision_id: int = Field(gt=0)


class AggregateThemeMetric(ReportContractModel):
    """Expose deterministic aggregate support for one Theme."""

    theme_id: NonEmptyString
    polarity: ThemePolarity
    support_count: int = Field(ge=0)
    total_support_percentage: float = Field(ge=0, le=100)
    oldest_support_percentage: float = Field(ge=0, le=100)
    newest_support_percentage: float = Field(ge=0, le=100)
    percentage_point_difference: float = Field(ge=-100, le=100)


class AggregateThemeMetrics(ReportContractModel):
    """Group all aggregate metrics and the visible polarity rankings."""

    all_themes: tuple[AggregateThemeMetric, ...]
    positive_headlines: tuple[AggregateThemeMetric, ...]
    negative_headlines: tuple[AggregateThemeMetric, ...]


class AggregateReport(ReportContractModel):
    """Store one current Version 3 Main Report or Test Report."""

    schema_version: Literal["3.0"]
    report_id: NonEmptyString
    kind: Literal["main", "test"]
    app_id: int = Field(gt=0)
    metadata_snapshot: SteamMetadata
    review_revision_ids: tuple[int, ...] = Field(min_length=1)
    oldest_review_revision_ids: tuple[int, ...]
    newest_review_revision_ids: tuple[int, ...]
    oversized_review_count: int = Field(default=0, ge=0)
    provider: NonEmptyString
    model: NonEmptyString
    contract_version: NonEmptyString
    themes: tuple[ThemeDefinition, ...]
    memberships: tuple[ThemeMembership, ...]
    theme_metrics: AggregateThemeMetrics

    @model_validator(mode="after")
    def require_consistent_scope(self) -> "AggregateReport":
        """Bind metadata, cohorts, Themes, and memberships to one exact scope."""

        scope_ids: set[int] = set(self.review_revision_ids)
        oldest_ids: set[int] = set(self.oldest_review_revision_ids)
        newest_ids: set[int] = set(self.newest_review_revision_ids)
        if len(scope_ids) != len(self.review_revision_ids) or any(
            identifier <= 0 for identifier in scope_ids
        ):
            raise ValueError("Report Review Revision identifiers must be unique and positive")
        if oldest_ids & newest_ids or oldest_ids | newest_ids != scope_ids:
            raise ValueError("Report cohorts must be non-overlapping and cover the scope")
        if self.metadata_snapshot.app_id != self.app_id:
            raise ValueError("Report metadata must match the report AppID")
        theme_ids: tuple[str, ...] = tuple(theme.theme_id for theme in self.themes)
        if len(theme_ids) != len(set(theme_ids)):
            raise ValueError("Report Theme identifiers must be unique")
        membership_pairs: tuple[tuple[str, int], ...] = tuple(
            (membership.theme_id, membership.review_revision_id)
            for membership in self.memberships
        )
        if len(membership_pairs) != len(set(membership_pairs)):
            raise ValueError("Report Theme Memberships must be unique")
        if any(
            theme_id not in set(theme_ids) or revision_id not in scope_ids
            for theme_id, revision_id in membership_pairs
        ):
            raise ValueError("Report Theme Membership is outside the report scope")
        metric_ids: set[str] = {
            metric.theme_id for metric in self.theme_metrics.all_themes
        }
        if metric_ids != set(theme_ids):
            raise ValueError("Report Theme metrics must match its Theme definitions")
        return self


class EvidenceFilterQuery(ReportContractModel):
    """Define temporary restrictions applied while exploring one report."""

    recommendation: Literal["all", "recommended", "not_recommended"] = "all"
    steam_purchase: bool | None = None
    received_for_free: bool | None = None
    written_during_early_access: bool | None = None
    playtime_basis: Literal["at_review", "current"] = "at_review"
    minimum_playtime_minutes: int | None = Field(default=None, ge=0)
    maximum_playtime_minutes: int | None = Field(default=None, ge=0)
    review_created_from: int | None = Field(default=None, ge=0)
    review_created_to: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_ordered_ranges(self) -> "EvidenceFilterQuery":
        """Reject bounds that cannot match a review."""

        if (
            self.minimum_playtime_minutes is not None
            and self.maximum_playtime_minutes is not None
            and self.minimum_playtime_minutes > self.maximum_playtime_minutes
        ):
            raise ValueError("minimum playtime cannot exceed maximum playtime")
        if (
            self.review_created_from is not None
            and self.review_created_to is not None
            and self.review_created_from > self.review_created_to
        ):
            raise ValueError("review start date cannot exceed end date")
        return self


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
    early_review_revision_ids: tuple[int, ...] = ()
    recent_review_revision_ids: tuple[int, ...] = ()
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
        early: set[int] = set(self.early_review_revision_ids)
        recent: set[int] = set(self.recent_review_revision_ids)
        if early & recent or (early | recent) not in (
            set(),
            set(self.review_revision_ids),
        ):
            raise ValueError("Report cohorts must be non-overlapping and cover the scope")
        return self
