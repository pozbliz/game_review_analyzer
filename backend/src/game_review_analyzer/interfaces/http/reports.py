"""Public report and complete-evidence response contracts."""

from pathlib import Path

from pydantic import BaseModel

from game_review_analyzer.application.theme_metrics import (
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
    EvidenceFilterQuery,
    MixedReceptionMetric,
    ReportVersion,
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


class ReportScopeResponse(BaseModel):
    """Expose the exact metric denominator and calibration state."""

    review_count: int
    thresholds_calibrated: bool


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
            thresholds_calibrated=report.thresholds_calibrated,
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
