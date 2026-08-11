"""Create immutable reports from validated analysis results."""

from collections.abc import Iterable
from pathlib import Path

from game_review_analyzer.application.manual_codex import (
    validate_manual_codex_result,
)
from game_review_analyzer.application.theme_metrics import calculate_theme_metrics
from game_review_analyzer.domain.analysis import AnalysisRequest, AnalysisResult
from game_review_analyzer.domain.reports import (
    ReportVersion,
    ThemeMetricPolicy,
    ThemeMetrics,
)
from game_review_analyzer.infrastructure.persistence.report_versions import (
    save_report_version,
)


def create_manual_codex_report(
    database_path: Path,
    report_version_id: str,
    request: AnalysisRequest,
    result_json: str,
    review_revision_ids: Iterable[int],
    metric_policy: ThemeMetricPolicy,
) -> ReportVersion:
    """Validate, calculate, and append one provisional Manual Codex report."""

    result: AnalysisResult = validate_manual_codex_result(request, result_json)
    metrics: ThemeMetrics = calculate_theme_metrics(
        (review.review_revision_id for review in request.reviews),
        result.opinion_points,
        result.themes,
        metric_policy,
    )
    report: ReportVersion = ReportVersion(
        schema_version="1.0",
        report_version_id=report_version_id,
        app_id=request.app_id,
        review_revision_ids=tuple(review_revision_ids),
        analysis_result=result,
        metric_policy=metric_policy,
        theme_metrics=metrics,
        thresholds_calibrated=False,
    )
    save_report_version(database_path, report)
    return report
