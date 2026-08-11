"""Versioned, identity-safe report export and local-evidence re-import."""

import csv
from hashlib import sha256
from html import escape
from io import StringIO
import json
import sqlite3
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, ValidationError, model_validator

from game_review_analyzer.domain.analysis import (
    NonEmptyString,
    OpinionPoint,
    Sha256Digest,
    Theme,
)
from game_review_analyzer.domain.reports import ReportContractModel, ReportVersion, ThemeMetric
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.infrastructure.persistence.game_datasets import load_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import (
    load_report_version,
    save_report_version,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
    match_review_revision_ids,
)

PRIVACY_WARNING: str = (
    "Full review text is included. This privacy-sensitive evidence must be shared deliberately."
)
OMISSION_NOTICE: str = "Full review text and reviewer identity are omitted by default."
# ponytail: export bodies are built in memory; stream them if measured report sizes cause pressure.


class ExportEvidenceBinding(ReportContractModel):
    """Bind one source review identifier to an exact normalized-content digest."""

    source_review_id: NonEmptyString
    content_sha256: Sha256Digest
    review_text: str | None = None


class JsonReportExport(ReportContractModel):
    """Carry one report snapshot plus fingerprints for strict local re-import."""

    kind: Literal["game-review-analyzer-report"]
    format_version: Literal["2.0"]
    full_review_text_included: bool
    privacy_warning: NonEmptyString
    report: ReportVersion
    evidence_bindings: tuple[ExportEvidenceBinding, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_evidence_manifest(self) -> "JsonReportExport":
        """Require one unique binding for every analyzed source review."""

        source_ids: tuple[str, ...] = tuple(
            binding.source_review_id for binding in self.evidence_bindings
        )
        expected_ids: tuple[str, ...] = self.report.analysis_result.completed_review_revision_ids
        if len(source_ids) != len(set(source_ids)) or set(source_ids) != set(expected_ids):
            raise ValueError("Evidence bindings must match the report analysis scope")
        has_all_text: bool = all(
            binding.review_text is not None for binding in self.evidence_bindings
        )
        if self.full_review_text_included != has_all_text:
            raise ValueError("Full-review-text option does not match the evidence bindings")
        return self


def export_report_json(
    database_path: Path,
    report_version_id: str,
    *,
    include_full_review_text: bool = False,
) -> str:
    """Serialize one immutable report with exact evidence fingerprints."""

    report: ReportVersion = required_report(database_path, report_version_id)
    reviews: dict[str, SteamReview] = reviews_by_source_id(database_path, report)
    bindings: tuple[ExportEvidenceBinding, ...] = tuple(
        ExportEvidenceBinding(
            source_review_id=review_id,
            content_sha256=review_digest(reviews[review_id]),
            review_text=reviews[review_id].text if include_full_review_text else None,
        )
        for review_id in report.analysis_result.completed_review_revision_ids
    )
    document = JsonReportExport(
        kind="game-review-analyzer-report",
        format_version="2.0",
        full_review_text_included=include_full_review_text,
        privacy_warning=PRIVACY_WARNING if include_full_review_text else OMISSION_NOTICE,
        report=report,
        evidence_bindings=bindings,
    )
    payload: dict[str, object] = document.model_dump(mode="json")
    if not include_full_review_text:
        for binding in payload["evidence_bindings"]:
            binding.pop("review_text")
    return json.dumps(payload, indent=2)


def import_report_json(database_path: Path, payload: str) -> ReportVersion:
    """Validate and append an exported report against exact local evidence."""

    try:
        document: JsonReportExport = JsonReportExport.model_validate_json(payload)
    except (ValidationError, ValueError) as error:
        raise ValueError("Invalid report export") from error
    if load_game_dataset(database_path, document.report.app_id) is None:
        raise ValueError("Matching local Game Dataset is unavailable")
    bindings: dict[str, str] = {
        item.source_review_id: item.content_sha256
        for item in document.evidence_bindings
    }
    local_ids: dict[str, int] = match_review_revision_ids(
        database_path, document.report.app_id, bindings
    )
    ordered_ids: tuple[int, ...] = tuple(
        local_ids[review_id]
        for review_id in document.report.analysis_result.completed_review_revision_ids
    )
    imported: ReportVersion = document.report.model_copy(
        update={"review_revision_ids": ordered_ids}
    )
    try:
        save_report_version(database_path, imported)
    except sqlite3.IntegrityError as error:
        raise ValueError("Report Version already exists") from error
    return imported


def export_report_csv(
    database_path: Path,
    report_version_id: str,
    *,
    include_full_review_text: bool = False,
) -> str:
    """Render one relationship-preserving Theme/evidence CSV."""

    report: ReportVersion = required_report(database_path, report_version_id)
    reviews: dict[str, SteamReview] = reviews_by_source_id(database_path, report)
    point_by_id: dict[str, OpinionPoint] = {
        point.id: point for point in report.analysis_result.opinion_points
    }
    metric_by_id: dict[str, ThemeMetric] = {
        metric.theme_id: metric for metric in report.theme_metrics.all_themes
    }
    fields: tuple[str, ...] = (
        "format_version", "report_version_id", "theme_id", "theme_title",
        "theme_polarity", "primary_category", "support_count", "support_percentage",
        "support_denominator", "opinion_point_id", "source_review_id", "excerpt",
        "sentiment", "subject", "review_text", "privacy_warning",
    )
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for theme in report.analysis_result.themes:
        metric: ThemeMetric = metric_by_id[theme.id]
        for point_id in theme.opinion_point_ids:
            point = point_by_id[point_id]
            row: dict[str, object] = {
                "format_version": "1.0",
                "report_version_id": report.report_version_id,
                "theme_id": theme.id,
                "theme_title": theme.title,
                "theme_polarity": theme.polarity.value,
                "primary_category": metric.primary_category.value,
                "support_count": metric.support_count,
                "support_percentage": metric.support_percentage,
                "support_denominator": len(report.review_revision_ids),
                "opinion_point_id": point.id,
                "source_review_id": point.review_revision_id,
                "excerpt": point.excerpt,
                "sentiment": point.sentiment.value,
                "subject": point.subject,
                "review_text": reviews[point.review_revision_id].text
                if include_full_review_text else "",
                "privacy_warning": PRIVACY_WARNING
                if include_full_review_text else OMISSION_NOTICE,
            }
            writer.writerow({key: csv_safe(value) for key, value in row.items()})
    return output.getvalue()


def export_report_html(database_path: Path, report_version_id: str) -> str:
    """Render escaped standalone HTML with optional external Steam media."""

    report: ReportVersion = required_report(database_path, report_version_id)
    metadata = report.metadata_snapshot
    theme_by_id: dict[str, Theme] = {
        theme.id: theme for theme in report.analysis_result.themes
    }
    point_by_id: dict[str, OpinionPoint] = {
        point.id: point for point in report.analysis_result.opinion_points
    }

    def section(title: str, metrics: tuple[ThemeMetric, ...]) -> str:
        items: str = "".join(
            theme_html(
                theme_by_id[metric.theme_id],
                metric,
                point_by_id,
                len(report.review_revision_ids),
            )
            for metric in metrics
        )
        return f"<section><h2>{escape(title)}</h2>{items or '<p>No themes.</p>'}</section>"

    media_url: str | None = safe_steam_image_url(metadata.capsule_image_url)
    media: str = (
        f'<img src="{escape(media_url, quote=True)}" alt="{escape(metadata.title)} Steam capsule">'
        if media_url else ""
    )
    body: str = "".join(
        (
            section("Positive themes", report.theme_metrics.positive_headlines),
            section("Negative themes", report.theme_metrics.negative_headlines),
            section("Technical themes", report.theme_metrics.technical_themes),
        )
    )
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<meta name=\"game-review-analyzer-format-version\" content=\"1.0\">"
        f"<title>{escape(metadata.title)} report</title>"
        "<style>body{max-width:70rem;margin:auto;padding:2rem;font:16px system-ui;line-height:1.5}"
        "article{border-top:1px solid #ccc;padding:1rem 0}small{color:#555}blockquote{margin-left:1rem}</style>"
        f"</head><body><header><h1>{escape(metadata.title)}</h1>{media}"
        f"<p>Report {escape(report.report_version_id)} · {len(report.review_revision_ids)} reviews</p>"
        "<p>External Steam-hosted media is not embedded and requires a network connection when shown.</p>"
        f"<p>{escape(OMISSION_NOTICE)}</p></header>{body}</body></html>"
    )


def required_report(database_path: Path, report_version_id: str) -> ReportVersion:
    """Load a report or fail with one application-level error."""

    report: ReportVersion | None = load_report_version(database_path, report_version_id)
    if report is None:
        raise ValueError("Report Version is unavailable")
    return report


def reviews_by_source_id(
    database_path: Path, report: ReportVersion
) -> dict[str, SteamReview]:
    """Load the report's exact revisions keyed by stable source review identifier."""

    revisions: dict[int, SteamReview] = load_review_revisions_by_ids(
        database_path, report.review_revision_ids
    )
    return {review.review_id: review for review in revisions.values()}


def review_digest(review: SteamReview) -> str:
    """Reproduce the normalized-content digest stored with a Review Revision."""

    return sha256(review.model_dump_json().encode("utf-8")).hexdigest()


def csv_safe(value: object) -> object:
    """Prevent spreadsheet software from evaluating untrusted cells as formulas."""

    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return f"'{value}"
    return value


def safe_steam_image_url(value: str | None) -> str | None:
    """Allow only HTTPS image hosts owned by Steam's static-media domain."""

    if value is None:
        return None
    parsed = urlparse(value)
    hostname: str = parsed.hostname or ""
    if parsed.scheme != "https" or not (
        hostname == "steamstatic.com" or hostname.endswith(".steamstatic.com")
    ):
        return None
    return value


def theme_html(
    theme: Theme,
    metric: ThemeMetric,
    point_by_id: dict[str, OpinionPoint],
    support_denominator: int,
) -> str:
    """Render one escaped Theme and its bounded representative evidence."""

    excerpts: str = "".join(
        f"<blockquote>{escape(point_by_id[point_id].excerpt)}</blockquote>"
        for point_id in theme.opinion_point_ids[:5]
    )
    return (
        f"<article><h3>{escape(theme.title)}</h3><p>{escape(theme.summary)}</p>"
        f"<small>{metric.support_count} reviews · {metric.support_percentage:g}% of "
        f"{support_denominator} · "
        f"{escape(metric.primary_category.value)}</small>{excerpts}</article>"
    )
