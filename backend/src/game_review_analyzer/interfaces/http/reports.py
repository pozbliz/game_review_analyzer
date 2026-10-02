"""Public Version 3 report response contracts."""

from typing import Literal

from pydantic import BaseModel

from game_review_analyzer.domain.analysis import ThemePolarity
from game_review_analyzer.domain.reports import (
    AggregateReport,
    AggregateThemeMetric,
    ThemeDefinition,
)
from game_review_analyzer.domain.steam_metadata import SteamMetadata


class ReportGameResponse(BaseModel):
    """Expose stable game identity for a report."""

    app_id: int
    title: str


class AggregateReportScopeResponse(BaseModel):
    """Expose the review counts used by one aggregate report."""

    review_count: int
    oldest_review_count: int
    newest_review_count: int
    oversized_review_count: int


class AggregateThemeResponse(BaseModel):
    """Expose one visible Theme and its deterministic aggregate metrics."""

    theme_id: str
    title: str
    summary: str
    polarity: ThemePolarity
    support_count: int
    total_support_percentage: float
    oldest_support_percentage: float
    newest_support_percentage: float
    percentage_point_difference: float


class AggregateReportResponse(BaseModel):
    """Expose a Version 3 report without internal analysis provenance."""

    schema_version: Literal["3.0"]
    report_id: str
    created_at: str
    kind: Literal["main", "test"]
    game: ReportGameResponse
    metadata: SteamMetadata
    scope: AggregateReportScopeResponse
    unseen_review_count: int | None = None
    positive_themes: tuple[AggregateThemeResponse, ...]
    negative_themes: tuple[AggregateThemeResponse, ...]


def build_aggregate_report_response(
    report: AggregateReport,
    created_at: str,
    unseen_review_count: int | None = None,
) -> AggregateReportResponse:
    """Build a public aggregate response without internal memberships."""

    themes_by_id: dict[str, ThemeDefinition] = {
        theme.theme_id: theme for theme in report.themes
    }

    def theme_response(metric: AggregateThemeMetric) -> AggregateThemeResponse:
        theme: ThemeDefinition = themes_by_id[metric.theme_id]
        return AggregateThemeResponse(
            theme_id=theme.theme_id,
            title=theme.title,
            summary=theme.summary,
            polarity=theme.polarity,
            support_count=metric.support_count,
            total_support_percentage=metric.total_support_percentage,
            oldest_support_percentage=metric.oldest_support_percentage,
            newest_support_percentage=metric.newest_support_percentage,
            percentage_point_difference=metric.percentage_point_difference,
        )

    return AggregateReportResponse(
        schema_version="3.0",
        report_id=report.report_id,
        created_at=created_at,
        kind=report.kind,
        game=ReportGameResponse(
            app_id=report.app_id,
            title=report.metadata_snapshot.title,
        ),
        metadata=report.metadata_snapshot,
        scope=AggregateReportScopeResponse(
            review_count=len(report.review_revision_ids),
            oldest_review_count=len(report.oldest_review_revision_ids),
            newest_review_count=len(report.newest_review_revision_ids),
            oversized_review_count=report.oversized_review_count,
        ),
        unseen_review_count=unseen_review_count,
        positive_themes=tuple(
            theme_response(metric)
            for metric in report.theme_metrics.positive_headlines
        ),
        negative_themes=tuple(
            theme_response(metric)
            for metric in report.theme_metrics.negative_headlines
        ),
    )
