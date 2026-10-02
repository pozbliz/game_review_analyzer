"""Immutable report snapshot and deterministic metric value contracts."""

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from game_review_analyzer.domain.analysis import ContractModel, NonEmptyString, ThemePolarity
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


class ThemeMetricPolicy(ReportContractModel):
    """Supply explicit thresholds and headline caps for one calculation."""

    minimum_support_count: int = Field(ge=1)
    minimum_support_percentage: float = Field(ge=0, le=100)
    technical_minimum_support_count: int = Field(ge=1)
    technical_minimum_support_percentage: float = Field(ge=0, le=100)
    maximum_headlines_per_polarity: int = Field(default=10, ge=1)


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
    metric_policy: ThemeMetricPolicy = Field(
        default_factory=lambda: ThemeMetricPolicy(
            minimum_support_count=1,
            minimum_support_percentage=5,
            technical_minimum_support_count=1,
            technical_minimum_support_percentage=5,
            maximum_headlines_per_polarity=10,
        )
    )
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
