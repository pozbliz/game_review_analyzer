"""Public report and complete-evidence response contracts."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from game_review_analyzer.application.theme_metrics import (
    calculate_theme_metrics,
    calculate_filtered_theme_metrics,
    review_matches_filter,
)
from game_review_analyzer.domain.analysis import (
    OpinionPoint,
    OpinionSentiment,
    Theme,
    ThemeCategory,
    ThemePolarity,
)
from game_review_analyzer.domain.reports import (
    AggregateReport,
    AggregateThemeMetric,
    EvidenceFilterQuery,
    MixedReceptionMetric,
    ReportVersion,
    ThemeDefinition,
    ThemeMetric,
)
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
)


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
    """Expose a Version 3 report without memberships or review evidence."""

    schema_version: Literal["3.0"]
    report_id: str
    created_at: str
    kind: Literal["main", "test"]
    game: ReportGameResponse
    metadata: SteamMetadata
    scope: AggregateReportScopeResponse
    provider: str
    model: str
    positive_themes: tuple[AggregateThemeResponse, ...]
    negative_themes: tuple[AggregateThemeResponse, ...]


class AggregateEvidenceReviewResponse(BaseModel):
    """Expose one complete local review supporting an aggregate Theme."""

    review_revision_id: int
    text: str
    recommended: bool
    votes_helpful: int


class AggregateThemeEvidenceResponse(BaseModel):
    """Expose helpful-first review evidence for one aggregate Theme."""

    theme_id: str
    title: str
    reviews: tuple[AggregateEvidenceReviewResponse, ...]


def build_aggregate_report_response(
    report: AggregateReport,
    created_at: str,
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
        provider=report.provider,
        model=report.model,
        positive_themes=tuple(
            theme_response(metric)
            for metric in report.theme_metrics.positive_headlines
        ),
        negative_themes=tuple(
            theme_response(metric)
            for metric in report.theme_metrics.negative_headlines
        ),
    )


def build_aggregate_theme_evidence_response(
    database_path: Path,
    report: AggregateReport,
    theme_id: str,
) -> AggregateThemeEvidenceResponse | None:
    """Join one aggregate Theme's memberships to helpful-first local reviews."""

    visible_theme_ids: set[str] = {
        metric.theme_id
        for metric in (
            report.theme_metrics.positive_headlines
            + report.theme_metrics.negative_headlines
        )
    }
    if theme_id not in visible_theme_ids:
        return None
    theme: ThemeDefinition | None = next(
        (item for item in report.themes if item.theme_id == theme_id), None
    )
    if theme is None:
        return None
    revision_ids: tuple[int, ...] = tuple(
        membership.review_revision_id
        for membership in report.memberships
        if membership.theme_id == theme_id
    )
    reviews_by_id: dict[int, SteamReview] = load_review_revisions_by_ids(
        database_path, revision_ids
    )
    ordered: tuple[tuple[int, SteamReview], ...] = tuple(sorted(
        reviews_by_id.items(),
        key=lambda item: (
            -item[1].votes_helpful,
            -item[1].source_created_at,
            item[0],
        ),
    ))
    return AggregateThemeEvidenceResponse(
        theme_id=theme.theme_id,
        title=theme.title,
        reviews=tuple(
            AggregateEvidenceReviewResponse(
                review_revision_id=revision_id,
                text=review.text,
                recommended=review.recommended,
                votes_helpful=review.votes_helpful,
            )
            for revision_id, review in ordered
        ),
    )


class ReportScopeResponse(BaseModel):
    """Expose the exact metric denominator and calibration state."""

    review_count: int
    opinion_point_count: int
    non_neutral_opinion_point_count: int
    thresholds_calibrated: bool
    early: "CohortScopeResponse | None" = None
    recent: "CohortScopeResponse | None" = None


class CohortScopeResponse(BaseModel):
    """Expose one immutable chronological cohort and its date extent."""

    review_count: int
    source_created_from: int
    source_created_to: int


class ReportProvenanceResponse(BaseModel):
    """Expose the provider result identity used to build a report."""

    provider: str
    model: str
    request_id: str
    scope_sha256: str


class ThemeSupportResponse(BaseModel):
    """Expose one Theme's support numerator, percentage, and denominator."""

    count: int
    percentage: float
    denominator: int


class RepresentativeEvidenceResponse(BaseModel):
    """Expose one exact representative Opinion Point."""

    opinion_point_id: str
    review_revision_id: str
    excerpt: str
    sentiment: OpinionSentiment


class ReportThemeResponse(BaseModel):
    """Expose one ranked Theme with bounded representative evidence."""

    theme_id: str
    title: str
    summary: str
    polarity: ThemePolarity
    primary_category: ThemeCategory
    related_categories: tuple[ThemeCategory, ...]
    support: ThemeSupportResponse
    below_threshold: bool
    evidence_count: int
    representative_evidence: tuple[RepresentativeEvidenceResponse, ...]
    opposes_theme_id: str | None
    cohort_comparison: "ThemeCohortComparisonResponse | None" = None


class ThemeCohortComparisonResponse(BaseModel):
    """Compare one Theme over the immutable early and recent denominators."""

    early: ThemeSupportResponse
    recent: ThemeSupportResponse
    percentage_point_change: float
    direction: Literal[
        "appears_improved",
        "mostly_unchanged",
        "appears_worse",
        "new_in_recent_reviews",
        "no_longer_prominent",
    ]


class MixedReceptionResponse(BaseModel):
    """Expose exact opposing-Theme reception numerators and denominators."""

    positive_theme_id: str
    negative_theme_id: str
    liked_count: int
    disliked_count: int
    mixed_count: int
    opinionated_review_count: int
    mentioned_review_count: int
    scope_review_count: int
    liked_percentage: float
    disliked_percentage: float
    mixed_percentage: float
    mentioned_percentage: float


class ReportResponse(BaseModel):
    """Expose one immutable report summary for initial exploration."""

    report_version_id: str
    game: ReportGameResponse
    metadata: SteamMetadata
    scope: ReportScopeResponse
    provenance: ReportProvenanceResponse
    positive_themes: tuple[ReportThemeResponse, ...]
    negative_themes: tuple[ReportThemeResponse, ...]
    technical_themes: tuple[ReportThemeResponse, ...]
    mixed_reception: tuple[MixedReceptionResponse, ...]


class EvidenceReviewResponse(BaseModel):
    """Expose locally stored source context without reviewer identity."""

    review_revision_id: str
    text: str
    source_created_at: int
    source_updated_at: int
    recommended: bool
    votes_helpful: int
    steam_purchase: bool
    received_for_free: bool
    written_during_early_access: bool
    playtime_forever_minutes: int
    playtime_at_review_minutes: int | None


class ThemeEvidenceItemResponse(BaseModel):
    """Join one Opinion Point to its complete immutable source review."""

    opinion_point_id: str
    excerpt: str
    sentiment: OpinionSentiment
    subject: str
    review: EvidenceReviewResponse


class ThemeEvidenceResponse(BaseModel):
    """Expose every stored Opinion Point supporting one Theme."""

    theme_id: str
    title: str
    items: tuple[ThemeEvidenceItemResponse, ...]


def build_report_response(
    database_path: Path,
    report: ReportVersion,
    query: EvidenceFilterQuery | None = None,
) -> ReportResponse:
    """Build a bounded report summary from one typed snapshot."""

    resolved_query: EvidenceFilterQuery = query or EvidenceFilterQuery()
    revisions_by_id: dict[int, SteamReview] = load_review_revisions_by_ids(
        database_path, report.review_revision_ids
    )
    matching_reviews: tuple[SteamReview, ...] = tuple(
        review
        for review in revisions_by_id.values()
        if review_matches_filter(review, resolved_query)
    )
    matching_review_ids: set[str] = {review.review_id for review in matching_reviews}
    metadata = report.metadata_snapshot
    theme_by_id: dict[str, Theme] = {
        theme.id: theme for theme in report.analysis_result.themes
    }
    point_by_id: dict[str, OpinionPoint] = {
        point.id: point for point in report.analysis_result.opinion_points
    }
    comparison_by_theme: dict[str, ThemeCohortComparisonResponse] = {}
    early_scope: CohortScopeResponse | None = None
    recent_scope: CohortScopeResponse | None = None
    if (
        resolved_query == EvidenceFilterQuery()
        and report.early_review_revision_ids
        and report.recent_review_revision_ids
    ):
        early_reviews: tuple[SteamReview, ...] = tuple(
            revisions_by_id[identifier]
            for identifier in report.early_review_revision_ids
        )
        recent_reviews: tuple[SteamReview, ...] = tuple(
            revisions_by_id[identifier]
            for identifier in report.recent_review_revision_ids
        )
        early_scope = cohort_scope(early_reviews)
        recent_scope = cohort_scope(recent_reviews)
        early_ids: set[str] = {review.review_id for review in early_reviews}
        recent_ids: set[str] = {review.review_id for review in recent_reviews}
        early_metrics = calculate_theme_metrics(
            early_ids,
            (
                point
                for point in report.analysis_result.opinion_points
                if point.review_revision_id in early_ids
            ),
            report.analysis_result.themes,
            report.metric_policy,
        )
        recent_metrics = calculate_theme_metrics(
            recent_ids,
            (
                point
                for point in report.analysis_result.opinion_points
                if point.review_revision_id in recent_ids
            ),
            report.analysis_result.themes,
            report.metric_policy,
        )
        early_by_id: dict[str, ThemeMetric] = {
            metric.theme_id: metric for metric in early_metrics.all_themes
        }
        recent_by_id: dict[str, ThemeMetric] = {
            metric.theme_id: metric for metric in recent_metrics.all_themes
        }
        comparison_by_theme = {
            theme.id: theme_comparison(
                theme,
                early_by_id[theme.id],
                recent_by_id[theme.id],
                len(early_reviews),
                len(recent_reviews),
            )
            for theme in report.analysis_result.themes
        }

    filtered_metrics = calculate_filtered_theme_metrics(
        revisions_by_id.values(),
        report.analysis_result.opinion_points,
        report.analysis_result.themes,
        report.metric_policy,
        resolved_query,
    )
    filtered: bool = resolved_query != EvidenceFilterQuery()

    def below_threshold(metric: ThemeMetric) -> bool:
        if metric.technical:
            return (
                metric.support_count < report.metric_policy.technical_minimum_support_count
                or metric.support_percentage
                < report.metric_policy.technical_minimum_support_percentage
            )
        return (
            metric.support_count < report.metric_policy.minimum_support_count
            or metric.support_percentage < report.metric_policy.minimum_support_percentage
        )

    def present(metric: ThemeMetric) -> ReportThemeResponse:
        theme: Theme = theme_by_id[metric.theme_id]
        matching_points: tuple[OpinionPoint, ...] = tuple(
            point_by_id[point_id]
            for point_id in theme.opinion_point_ids
            if point_by_id[point_id].review_revision_id in matching_review_ids
        )
        representative_points: tuple[OpinionPoint, ...] = matching_points[:5]
        return ReportThemeResponse(
            theme_id=theme.id,
            title=theme.title,
            summary=theme.summary,
            polarity=theme.polarity,
            primary_category=metric.primary_category,
            related_categories=metric.related_categories,
            support=ThemeSupportResponse(
                count=metric.support_count,
                percentage=metric.support_percentage,
                denominator=len(matching_reviews),
            ),
            below_threshold=below_threshold(metric),
            evidence_count=len(matching_points),
            representative_evidence=tuple(
                RepresentativeEvidenceResponse(
                    opinion_point_id=point.id,
                    review_revision_id=point.review_revision_id,
                    excerpt=point.excerpt,
                    sentiment=point.sentiment,
                )
                for point in representative_points
            ),
            opposes_theme_id=theme.opposes_theme_id,
            cohort_comparison=comparison_by_theme.get(theme.id),
        )

    result = report.analysis_result
    if filtered:
        ranked: tuple[ThemeMetric, ...] = tuple(
            sorted(
                (metric for metric in filtered_metrics.all_themes if metric.support_count),
                key=lambda metric: (-metric.support_count, metric.theme_id),
            )
        )
        positive_metrics: tuple[ThemeMetric, ...] = tuple(
            metric
            for metric in ranked
            if not metric.technical and metric.polarity == ThemePolarity.POSITIVE
        )[: report.metric_policy.maximum_headlines_per_polarity]
        negative_metrics: tuple[ThemeMetric, ...] = tuple(
            metric
            for metric in ranked
            if not metric.technical and metric.polarity == ThemePolarity.NEGATIVE
        )[: report.metric_policy.maximum_headlines_per_polarity]
        technical_metrics: tuple[ThemeMetric, ...] = tuple(
            metric for metric in ranked if metric.technical
        )
    else:
        positive_metrics = report.theme_metrics.positive_headlines
        negative_metrics = report.theme_metrics.negative_headlines
        technical_metrics = report.theme_metrics.technical_themes
    return ReportResponse(
        report_version_id=report.report_version_id,
        game=ReportGameResponse(app_id=report.app_id, title=metadata.title),
        metadata=metadata,
        scope=ReportScopeResponse(
            review_count=len(matching_reviews),
            opinion_point_count=len(result.opinion_points),
            non_neutral_opinion_point_count=sum(
                point.sentiment != OpinionSentiment.NEUTRAL
                for point in result.opinion_points
            ),
            thresholds_calibrated=report.thresholds_calibrated,
            early=early_scope,
            recent=recent_scope,
        ),
        provenance=ReportProvenanceResponse(
            provider=result.provider,
            model=result.model,
            request_id=result.request_id,
            scope_sha256=result.scope_sha256,
        ),
        positive_themes=tuple(present(item) for item in positive_metrics),
        negative_themes=tuple(present(item) for item in negative_metrics),
        technical_themes=tuple(present(item) for item in technical_metrics),
        mixed_reception=tuple(
            MixedReceptionResponse(**item.model_dump())
            for item in filtered_metrics.mixed_reception
        ),
    )


def cohort_scope(reviews: tuple[SteamReview, ...]) -> CohortScopeResponse:
    """Summarize the immutable date extent of one non-empty cohort."""

    timestamps: tuple[int, ...] = tuple(
        review.source_created_at for review in reviews
    )
    return CohortScopeResponse(
        review_count=len(reviews),
        source_created_from=min(timestamps),
        source_created_to=max(timestamps),
    )


def theme_comparison(
    theme: Theme,
    early: ThemeMetric,
    recent: ThemeMetric,
    early_denominator: int,
    recent_denominator: int,
) -> ThemeCohortComparisonResponse:
    """Calculate one conservative, polarity-aware cohort direction label."""

    change: float = recent.support_percentage - early.support_percentage
    meaningful_count: int = 2
    if early.support_count == 0 and recent.support_count >= meaningful_count:
        direction = "new_in_recent_reviews"
    elif recent.support_count == 0 and early.support_count >= meaningful_count:
        direction = "no_longer_prominent"
    elif abs(change) < 5:
        direction = "mostly_unchanged"
    elif (change > 0) == (theme.polarity == ThemePolarity.NEGATIVE):
        direction = "appears_worse"
    else:
        direction = "appears_improved"
    return ThemeCohortComparisonResponse(
        early=ThemeSupportResponse(
            count=early.support_count,
            percentage=early.support_percentage,
            denominator=early_denominator,
        ),
        recent=ThemeSupportResponse(
            count=recent.support_count,
            percentage=recent.support_percentage,
            denominator=recent_denominator,
        ),
        percentage_point_change=change,
        direction=direction,
    )


def build_theme_evidence_response(
    database_path: Path,
    report: ReportVersion,
    theme_id: str,
    query: EvidenceFilterQuery | None = None,
) -> ThemeEvidenceResponse | None:
    """Join all Theme Opinion Points to their exact stored review context."""

    theme: Theme | None = next(
        (item for item in report.analysis_result.themes if item.id == theme_id), None
    )
    if theme is None:
        return None
    revisions_by_id: dict[int, SteamReview] = load_review_revisions_by_ids(
        database_path, report.review_revision_ids
    )
    review_by_source_id: dict[str, SteamReview] = {
        review.review_id: review
        for review in revisions_by_id.values()
        if review_matches_filter(review, query or EvidenceFilterQuery())
    }
    point_by_id: dict[str, OpinionPoint] = {
        point.id: point for point in report.analysis_result.opinion_points
    }
    return ThemeEvidenceResponse(
        theme_id=theme.id,
        title=theme.title,
        items=tuple(
            evidence_item(point_by_id[point_id], review_by_source_id)
            for point_id in theme.opinion_point_ids
            if point_by_id[point_id].review_revision_id in review_by_source_id
        ),
    )


def evidence_item(
    point: OpinionPoint,
    review_by_source_id: dict[str, SteamReview],
) -> ThemeEvidenceItemResponse:
    """Build one evidence item from already validated snapshot relationships."""

    review: SteamReview = review_by_source_id[point.review_revision_id]
    return ThemeEvidenceItemResponse(
        opinion_point_id=point.id,
        excerpt=point.excerpt,
        sentiment=point.sentiment,
        subject=point.subject,
        review=EvidenceReviewResponse(
            review_revision_id=review.review_id,
            text=review.text,
            source_created_at=review.source_created_at,
            source_updated_at=review.source_updated_at,
            recommended=review.recommended,
            votes_helpful=review.votes_helpful,
            steam_purchase=review.steam_purchase,
            received_for_free=review.received_for_free,
            written_during_early_access=review.written_during_early_access,
            playtime_forever_minutes=review.playtime_forever_minutes,
            playtime_at_review_minutes=review.playtime_at_review_minutes,
        ),
    )
