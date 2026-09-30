"""Durable provider analysis-to-report runner."""

import json
from collections.abc import Iterator
from pathlib import Path
from time import monotonic
from typing import Protocol, runtime_checkable

from game_review_analyzer.application.manual_codex import build_analysis_request
from game_review_analyzer.application.main_report import pack_review_batches
from game_review_analyzer.application.opinion_consolidation import (
    exclude_known_generic_opinion_points,
)
from game_review_analyzer.application.report_creation import create_report
from game_review_analyzer.application.provider import (
    AnalysisProviderError,
    build_theme_merge_request,
    build_theme_analysis_request,
    CancellationSignal,
    ExtractionProviderRun,
    ProviderRun,
    ThemeProviderRun,
    ThemeMergeProviderRun,
    ProviderUsage,
    validate_theme_merge_result,
    validate_theme_provider_result,
)
from game_review_analyzer.application.theme_metrics import calculate_aggregate_theme_metrics
from game_review_analyzer.domain.analysis import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisSourceReview,
    ANALYSIS_CONTRACT_VERSION,
    ExtractedOpinionPoint,
    ThemeAnalysisRequest,
    ThemeMergeCandidate,
    ThemeMergeRequest,
    ThemeMergeTheme,
)
from game_review_analyzer.domain.reports import (
    AggregateReport,
    AggregateThemeMetrics,
    ThemeDefinition,
    ThemeMembership,
)
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.analysis_runs import (
    AnalysisRun,
    finish_analysis_run,
    get_analysis_run,
    start_analysis_run,
)
from game_review_analyzer.infrastructure.persistence.game_datasets import load_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import (
    load_aggregate_report_slot,
    load_report_version,
    save_aggregate_report,
)
from game_review_analyzer.infrastructure.persistence.opinion_extractions import (
    load_opinion_extractions,
    save_opinion_extraction_batch,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
)
from game_review_analyzer.infrastructure.persistence.theme_batches import (
    load_theme_batch,
    save_theme_batch,
)
from game_review_analyzer.shared.telemetry import TRACER, log_event


EXTRACTION_CONTRACT_VERSION = "2.0"


@runtime_checkable
class AnalysisProvider(Protocol):
    """Describe the provider behavior required by the durable runner."""

    model: str

    def analyze(
        self, request: AnalysisRequest, *, cancel_event: CancellationSignal
    ) -> ProviderRun:
        """Return one validated analysis result."""

    def extract(
        self, request: AnalysisRequest, *, cancel_event: CancellationSignal
    ) -> ExtractionProviderRun:
        """Return validated Opinion Points for one bounded review batch."""

    def consolidate(
        self, request: AnalysisRequest, *, cancel_event: CancellationSignal
    ) -> ProviderRun:
        """Return shared Themes over already validated Opinion Points."""


@runtime_checkable
class ThemeAnalysisProvider(Protocol):
    """Describe the provider behavior required by Version 3 reports."""

    model: str

    def analyze_themes(
        self, request: ThemeAnalysisRequest, *, cancel_event: CancellationSignal
    ) -> ThemeProviderRun:
        """Return Version 3 Theme candidates for one complete batch."""


@runtime_checkable
class ThemeMergeProvider(Protocol):
    """Describe the provider behavior required to merge mapped candidates."""

    model: str

    def merge_themes(
        self, request: ThemeMergeRequest, *, cancel_event: CancellationSignal
    ) -> ThemeMergeProviderRun:
        """Return mappings for every validated map candidate."""


class _DurableCancellation:
    def __init__(self, database_path: Path, run_id: str) -> None:
        self._database_path = database_path
        self._run_id = run_id

    def is_set(self) -> bool:
        return get_analysis_run(self._database_path, self._run_id).cancel_requested


class AnalysisRunner:
    """Run one queued provider analysis and persist its immutable report."""

    def __init__(
        self,
        database_path: Path,
        provider: AnalysisProvider | ThemeAnalysisProvider,
        *,
        batch_review_limit: int = 50,
        batch_character_limit: int = 32_000,
    ) -> None:
        self._database_path = database_path
        self._provider = provider
        self._batch_review_limit = batch_review_limit
        self._batch_character_limit = batch_character_limit

    def run(self, run_id: str) -> None:
        started_at: float = monotonic()
        run = start_analysis_run(self._database_path, run_id)
        if run is None:
            return
        log_event(
            "analysis.started",
            run_id=run.id,
            app_id=run.app_id,
            provider=run.provider,
            model=run.model,
            review_count=len(run.review_revision_ids),
        )
        with TRACER.start_as_current_span(
            "analysis.run",
            attributes={
                "analysis.run.id": run.id,
                "game.app_id": run.app_id,
                "analysis.provider": run.provider,
                "analysis.model": run.model,
                "analysis.review.count": len(run.review_revision_ids),
            },
        ):
            self._run_started(run, started_at)

    def _run_started(self, run: AnalysisRun, started_at: float) -> None:
        if run.report_kind == "test":
            self._run_test_report(run, started_at)
            return
        if run.report_kind == "main":
            self._run_main_report(run, started_at)
            return
        report_id = f"analysis-{run.id}"
        if load_report_version(self._database_path, report_id) is not None:
            finish_analysis_run(
                self._database_path, run.id, "completed", report_version_id=report_id
            )
            return
        try:
            preparation_started_at: float = monotonic()
            metadata: SteamMetadata | None = load_game_dataset(
                self._database_path, run.app_id
            )
            if metadata is None:
                raise ValueError("Matching Game Dataset metadata is unavailable")
            revisions = load_review_revisions_by_ids(
                self._database_path, run.review_revision_ids
            )
            cancellation: _DurableCancellation = _DurableCancellation(
                self._database_path, run.id
            )
            cached = load_opinion_extractions(
                self._database_path,
                revision_ids=run.review_revision_ids,
                provider=run.provider,
                model=run.model,
                contract_version=EXTRACTION_CONTRACT_VERSION,
            )
            pending_revision_ids: tuple[int, ...] = tuple(
                revision_id
                for revision_id in run.review_revision_ids
                if revision_id not in cached
            )
            completed_review_count: int = len(cached)
            log_event(
                "analysis.prepared",
                run_id=run.id,
                duration_ms=round((monotonic() - preparation_started_at) * 1000),
                cached_review_count=completed_review_count,
                pending_review_count=len(pending_revision_ids),
            )
            input_tokens: int = 0
            cached_input_tokens: int = 0
            output_tokens: int = 0
            for batch_number, batch_revision_ids in enumerate(
                self._batches(pending_revision_ids, revisions), start=1
            ):
                batch_started_at: float = monotonic()
                batch_request = build_analysis_request(
                    request_id=f"{run.id}-extract-{batch_number}",
                    app_id=run.app_id,
                    game_title=metadata.title,
                    reviews=(
                        AnalysisSourceReview(
                            review_revision_id=revisions[revision_id].review_id,
                            text=revisions[revision_id].text,
                        )
                        for revision_id in batch_revision_ids
                    ),
                )
                with TRACER.start_as_current_span(
                    "analysis.extract.batch",
                    attributes={
                        "analysis.run.id": run.id,
                        "analysis.batch.number": batch_number,
                        "analysis.batch.review.count": len(batch_revision_ids),
                        "analysis.batch.character.count": sum(
                            len(revisions[revision_id].text)
                            for revision_id in batch_revision_ids
                        ),
                    },
                ):
                    provider_started_at: float = monotonic()
                    extraction = self._analysis_provider().extract(
                        batch_request, cancel_event=cancellation
                    )
                    provider_duration_ms: int = round(
                        (monotonic() - provider_started_at) * 1000
                    )
                cache_started_at: float = monotonic()
                save_opinion_extraction_batch(
                    self._database_path,
                    revision_ids_by_review_id={
                        revisions[revision_id].review_id: revision_id
                        for revision_id in batch_revision_ids
                    },
                    result=extraction.result,
                    contract_version=EXTRACTION_CONTRACT_VERSION,
                )
                cache_duration_ms: int = round(
                    (monotonic() - cache_started_at) * 1000
                )
                completed_review_count += len(batch_revision_ids)
                log_event(
                    "analysis.extraction_batch_completed",
                    run_id=run.id,
                    batch_number=batch_number,
                    review_count=len(batch_revision_ids),
                    completed_review_count=completed_review_count,
                    provider_duration_ms=provider_duration_ms,
                    cache_duration_ms=cache_duration_ms,
                    duration_ms=round((monotonic() - batch_started_at) * 1000),
                )
                input_tokens += extraction.usage.input_tokens or 0
                cached_input_tokens += extraction.usage.cached_input_tokens or 0
                output_tokens += extraction.usage.output_tokens or 0
            cached = load_opinion_extractions(
                self._database_path,
                revision_ids=run.review_revision_ids,
                provider=run.provider,
                model=run.model,
                contract_version=EXTRACTION_CONTRACT_VERSION,
            )
            specific_points: tuple[ExtractedOpinionPoint, ...] = (
                exclude_known_generic_opinion_points(
                    tuple(
                        point
                        for revision_id in run.review_revision_ids
                        for point in cached[revision_id]
                    )
                )
            )
            specific_points_by_revision: dict[int, list[ExtractedOpinionPoint]] = {
                revision_id: [] for revision_id in run.review_revision_ids
            }
            revision_id_by_review_id: dict[str, int] = {
                revisions[revision_id].review_id: revision_id
                for revision_id in run.review_revision_ids
            }
            for point in specific_points:
                specific_points_by_revision[
                    revision_id_by_review_id[point.review_revision_id]
                ].append(point)
            request = build_analysis_request(
                request_id=run.id,
                app_id=run.app_id,
                game_title=metadata.title,
                reviews=(
                    AnalysisSourceReview(
                        review_revision_id=revisions[revision_id].review_id,
                        text=json.dumps(
                            {
                                "cohort": (
                                    "early"
                                    if revision_id in run.early_review_revision_ids
                                    else "recent"
                                ),
                                "opinion_points": [
                                    point.model_dump(mode="json")
                                    for point in specific_points_by_revision[revision_id]
                                ],
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    )
                    for revision_id in run.review_revision_ids
                ),
            )
            with TRACER.start_as_current_span(
                "analysis.consolidate",
                attributes={
                    "analysis.run.id": run.id,
                    "analysis.opinion_point.count": sum(map(len, cached.values())),
                },
            ):
                consolidation_started_at: float = monotonic()
                if specific_points:
                    consolidation = self._analysis_provider().consolidate(
                        request,
                        cancel_event=cancellation,
                    )
                    result = consolidation.result
                    input_tokens += consolidation.usage.input_tokens or 0
                    cached_input_tokens += consolidation.usage.cached_input_tokens or 0
                    output_tokens += consolidation.usage.output_tokens or 0
                else:
                    result = AnalysisResult(
                        schema_version="1.0",
                        request_id=request.request_id,
                        scope_sha256=request.scope_sha256,
                        provider=run.provider,
                        model=run.model,
                        completed_review_revision_ids=tuple(
                            review.review_revision_id for review in request.reviews
                        ),
                        opinion_points=(),
                        themes=(),
                        mechanic_classifications=(),
                    )
                log_event(
                    "analysis.consolidation_completed",
                    run_id=run.id,
                    opinion_point_count=len(specific_points),
                    duration_ms=round(
                        (monotonic() - consolidation_started_at) * 1000
                    ),
                )
            if cancellation.is_set():
                finish_analysis_run(self._database_path, run.id, "cancelled")
                log_event(
                    "analysis.cancelled",
                    run_id=run.id,
                    duration_ms=round((monotonic() - started_at) * 1000),
                )
                return
            if result.provider != run.provider or result.model != run.model:
                raise ValueError("Provider result provenance does not match the run")
            with TRACER.start_as_current_span(
                "analysis.create_report",
                attributes={
                    "analysis.run.id": run.id,
                    "analysis.theme.count": len(result.themes),
                },
            ):
                report_started_at: float = monotonic()
                create_report(
                    self._database_path,
                    report_id,
                    request,
                    result,
                    run.review_revision_ids,
                    run.metric_policy,
                    early_review_revision_ids=run.early_review_revision_ids,
                    recent_review_revision_ids=run.recent_review_revision_ids,
                )
                log_event(
                    "analysis.report_persisted",
                    run_id=run.id,
                    theme_count=len(result.themes),
                    duration_ms=round((monotonic() - report_started_at) * 1000),
                )
            finish_analysis_run(
                self._database_path,
                run.id,
                "completed",
                report_version_id=report_id,
                input_tokens=input_tokens,
                cached_input_tokens=cached_input_tokens,
                output_tokens=output_tokens,
            )
            log_event(
                "analysis.completed",
                run_id=run.id,
                duration_ms=round((monotonic() - started_at) * 1000),
                input_tokens=input_tokens,
                cached_input_tokens=cached_input_tokens,
                output_tokens=output_tokens,
                theme_count=len(result.themes),
            )
        except AnalysisProviderError as error:
            state = "cancelled" if error.code == "cancelled" else "failed"
            finish_analysis_run(self._database_path, run.id, state, error_code=error.code)
            log_event(
                f"analysis.{state}",
                level="error" if state == "failed" else "info",
                run_id=run.id,
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code=error.code,
            )
        except ValueError as error:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="invalid_analysis_scope"
            )
            log_event(
                "analysis.failed",
                level="error",
                run_id=run.id,
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code="invalid_analysis_scope",
                error_type=type(error).__name__,
            )
        except Exception as error:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="internal_analysis_error"
            )
            log_event(
                "analysis.failed",
                level="error",
                run_id=run.id,
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code="internal_analysis_error",
                error_type=type(error).__name__,
            )

    def _run_main_report(self, run: AnalysisRun, started_at: float) -> None:
        report_id: str = f"analysis-{run.id}"
        current_report: AggregateReport | None = load_aggregate_report_slot(
            self._database_path, run.app_id, "main"
        )
        if current_report is not None and current_report.report_id == report_id:
            finish_analysis_run(
                self._database_path, run.id, "completed", report_version_id=report_id
            )
            return
        extension_report: AggregateReport | None = (
            current_report
            if current_report is not None
            and set(run.review_revision_ids).isdisjoint(
                current_report.review_revision_ids
            )
            else None
        )
        try:
            metadata: SteamMetadata | None = load_game_dataset(
                self._database_path, run.app_id
            )
            if metadata is None:
                raise ValueError("Matching Game Dataset metadata is unavailable")
            revisions: dict[int, SteamReview] = load_review_revisions_by_ids(
                self._database_path, run.review_revision_ids
            )
            cancellation: _DurableCancellation = _DurableCancellation(
                self._database_path, run.id
            )
            map_runs: list[ThemeProviderRun] = []
            merge_candidates: list[ThemeMergeCandidate] = []
            for batch_number, batch_revision_ids in enumerate(
                self._batches(run.review_revision_ids, revisions), start=1
            ):
                request: ThemeAnalysisRequest = build_theme_analysis_request(
                    request_id=f"{run.id}-map-{batch_number}",
                    app_id=run.app_id,
                    game_title=metadata.title,
                    reviews=(
                        AnalysisSourceReview(
                            review_revision_id=revisions[revision_id].review_id,
                            text=revisions[revision_id].text,
                        )
                        for revision_id in batch_revision_ids
                    ),
                )
                provider_run: ThemeProviderRun | None = load_theme_batch(
                    self._database_path,
                    run_id=run.id,
                    batch_number=batch_number,
                    input_digest=request.scope_sha256,
                    provider=run.provider,
                    model=run.model,
                    contract_version=ANALYSIS_CONTRACT_VERSION,
                )
                if provider_run is None:
                    provider_run = self._theme_provider().analyze_themes(
                        request,
                        cancel_event=cancellation,
                    )
                    validate_theme_provider_result(
                        request,
                        provider_run.result,
                        expected_provider=run.provider,
                        expected_model=run.model,
                    )
                    save_theme_batch(
                        self._database_path,
                        run_id=run.id,
                        batch_number=batch_number,
                        input_digest=request.scope_sha256,
                        provider=run.provider,
                        model=run.model,
                        contract_version=ANALYSIS_CONTRACT_VERSION,
                        provider_run=provider_run,
                    )
                map_runs.append(provider_run)
                merge_candidates.extend(
                    ThemeMergeCandidate(
                        candidate_key=f"{batch_number}:{candidate.candidate_id}",
                        title=candidate.title,
                        summary=candidate.summary,
                        polarity=candidate.polarity,
                        supporting_review_revision_ids=(
                            candidate.supporting_review_revision_ids
                        ),
                    )
                    for candidate in provider_run.result.themes
                )

            merge_usage: ProviderUsage = ProviderUsage(None, None, None)
            themes: tuple[ThemeDefinition, ...] = (
                extension_report.themes if extension_report is not None else ()
            )
            memberships: tuple[ThemeMembership, ...] = (
                extension_report.memberships if extension_report is not None else ()
            )
            if merge_candidates:
                merge_request: ThemeMergeRequest = build_theme_merge_request(
                    request_id=f"{run.id}-merge",
                    app_id=run.app_id,
                    game_title=metadata.title,
                    candidates=merge_candidates,
                    established_themes=(
                        ThemeMergeTheme(
                            theme_id=theme.theme_id,
                            title=theme.title,
                            summary=theme.summary,
                            polarity=theme.polarity,
                        )
                        for theme in themes
                    ),
                )
                merge_run: ThemeMergeProviderRun = (
                    self._theme_merge_provider().merge_themes(
                        merge_request,
                        cancel_event=cancellation,
                    )
                )
                validate_theme_merge_result(
                    merge_request,
                    merge_run.result,
                    expected_provider=run.provider,
                    expected_model=run.model,
                )
                merge_usage = merge_run.usage
                candidate_by_key: dict[str, ThemeMergeCandidate] = {
                    candidate.candidate_key: candidate
                    for candidate in merge_candidates
                }
                revision_id_by_review_id: dict[str, int] = {
                    review.review_id: revision_id
                    for revision_id, review in revisions.items()
                }
                themes = tuple(
                    ThemeDefinition(
                        theme_id=theme.theme_id,
                        title=theme.title,
                        summary=theme.summary,
                        polarity=theme.polarity,
                    )
                    for theme in merge_run.result.themes
                )
                membership_pairs: set[tuple[str, int]] = {
                    (
                        assignment.theme_id,
                        revision_id_by_review_id[review_id],
                    )
                    for assignment in merge_run.result.assignments
                    if assignment.theme_id is not None
                    for review_id in candidate_by_key[
                        assignment.candidate_key
                    ].supporting_review_revision_ids
                }
                new_memberships: tuple[ThemeMembership, ...] = tuple(
                    ThemeMembership(
                        theme_id=theme_id,
                        review_revision_id=revision_id,
                    )
                    for theme_id, revision_id in sorted(membership_pairs)
                )
                memberships += new_memberships

            review_revision_ids: tuple[int, ...] = (
                (extension_report.review_revision_ids if extension_report else ())
                + run.review_revision_ids
            )
            oldest_revision_ids: tuple[int, ...] = (
                (extension_report.oldest_review_revision_ids if extension_report else ())
                + run.early_review_revision_ids
            )
            newest_revision_ids: tuple[int, ...] = (
                (extension_report.newest_review_revision_ids if extension_report else ())
                + run.recent_review_revision_ids
            )

            all_metrics: AggregateThemeMetrics = calculate_aggregate_theme_metrics(
                review_revision_ids,
                oldest_revision_ids,
                newest_revision_ids,
                themes,
                memberships,
                run.metric_policy,
            )
            retained_ids: set[str] = {
                metric.theme_id
                for metric in all_metrics.all_themes
                if max(
                    metric.oldest_support_percentage,
                    metric.newest_support_percentage,
                )
                >= 2
            }
            retained_themes: tuple[ThemeDefinition, ...] = tuple(
                theme for theme in themes if theme.theme_id in retained_ids
            )
            retained_memberships: tuple[ThemeMembership, ...] = tuple(
                membership
                for membership in memberships
                if membership.theme_id in retained_ids
            )
            retained_metrics: AggregateThemeMetrics = (
                calculate_aggregate_theme_metrics(
                    review_revision_ids,
                    oldest_revision_ids,
                    newest_revision_ids,
                    retained_themes,
                    retained_memberships,
                    run.metric_policy,
                )
            )
            report: AggregateReport = AggregateReport(
                schema_version="3.0",
                report_id=report_id,
                kind="main",
                app_id=run.app_id,
                metadata_snapshot=metadata,
                review_revision_ids=review_revision_ids,
                oldest_review_revision_ids=oldest_revision_ids,
                newest_review_revision_ids=newest_revision_ids,
                oversized_review_count=(
                    (extension_report.oversized_review_count if extension_report else 0)
                    + run.oversized_review_count
                ),
                provider=run.provider,
                model=run.model,
                contract_version=ANALYSIS_CONTRACT_VERSION,
                metric_policy=run.metric_policy,
                themes=retained_themes,
                memberships=retained_memberships,
                theme_metrics=retained_metrics,
            )
            save_aggregate_report(self._database_path, report)
            usages: tuple[ProviderUsage, ...] = tuple(
                provider_run.usage for provider_run in map_runs
            ) + (merge_usage,)
            finish_analysis_run(
                self._database_path,
                run.id,
                "completed",
                report_version_id=report_id,
                input_tokens=_sum_usage(usages, "input_tokens"),
                cached_input_tokens=_sum_usage(usages, "cached_input_tokens"),
                output_tokens=_sum_usage(usages, "output_tokens"),
            )
            log_event(
                "analysis.completed",
                run_id=run.id,
                report_kind="main",
                duration_ms=round((monotonic() - started_at) * 1000),
                theme_count=len(retained_themes),
            )
        except AnalysisProviderError as error:
            state = "cancelled" if error.code == "cancelled" else "failed"
            finish_analysis_run(self._database_path, run.id, state, error_code=error.code)
            log_event(
                f"analysis.{state}",
                level="error" if state == "failed" else "info",
                run_id=run.id,
                report_kind="main",
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code=error.code,
                error_type=type(error).__name__,
            )
        except ValueError as error:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="invalid_theme_result"
            )
            log_event(
                "analysis.failed",
                level="error",
                run_id=run.id,
                report_kind="main",
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code="invalid_theme_result",
                error_type=type(error).__name__,
            )
        except Exception as error:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="internal_analysis_error"
            )
            log_event(
                "analysis.failed",
                level="error",
                run_id=run.id,
                report_kind="main",
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code="internal_analysis_error",
                error_type=type(error).__name__,
            )

    def _run_test_report(self, run: AnalysisRun, started_at: float) -> None:
        report_id: str = f"analysis-{run.id}"
        current_report: AggregateReport | None = load_aggregate_report_slot(
            self._database_path, run.app_id, "test"
        )
        if current_report is not None and current_report.report_id == report_id:
            finish_analysis_run(
                self._database_path, run.id, "completed", report_version_id=report_id
            )
            return
        try:
            metadata = load_game_dataset(self._database_path, run.app_id)
            if metadata is None:
                raise ValueError("Matching Game Dataset metadata is unavailable")
            revisions: dict[int, SteamReview] = load_review_revisions_by_ids(
                self._database_path, run.review_revision_ids
            )
            request = build_theme_analysis_request(
                request_id=run.id,
                app_id=run.app_id,
                game_title=metadata.title,
                reviews=(
                    AnalysisSourceReview(
                        review_revision_id=revisions[revision_id].review_id,
                        text=revisions[revision_id].text,
                    )
                    for revision_id in run.review_revision_ids
                ),
            )
            provider_run: ThemeProviderRun = self._theme_provider().analyze_themes(
                request,
                cancel_event=_DurableCancellation(self._database_path, run.id),
            )
            validate_theme_provider_result(
                request,
                provider_run.result,
                expected_provider=run.provider,
                expected_model=run.model,
            )
            revision_id_by_review_id: dict[str, int] = {
                review.review_id: revision_id
                for revision_id, review in revisions.items()
            }
            themes: tuple[ThemeDefinition, ...] = tuple(
                ThemeDefinition(
                    theme_id=candidate.candidate_id,
                    title=candidate.title,
                    summary=candidate.summary,
                    polarity=candidate.polarity,
                )
                for candidate in provider_run.result.themes
            )
            memberships: tuple[ThemeMembership, ...] = tuple(
                ThemeMembership(
                    theme_id=candidate.candidate_id,
                    review_revision_id=revision_id_by_review_id[review_id],
                )
                for candidate in provider_run.result.themes
                for review_id in candidate.supporting_review_revision_ids
            )
            all_metrics: AggregateThemeMetrics = calculate_aggregate_theme_metrics(
                run.review_revision_ids,
                run.early_review_revision_ids,
                run.recent_review_revision_ids,
                themes,
                memberships,
                run.metric_policy,
            )
            visible_ids: set[str] = {
                metric.theme_id
                for metric in (
                    all_metrics.positive_headlines + all_metrics.negative_headlines
                )
            }
            visible_themes: tuple[ThemeDefinition, ...] = tuple(
                theme for theme in themes if theme.theme_id in visible_ids
            )
            visible_memberships: tuple[ThemeMembership, ...] = tuple(
                membership
                for membership in memberships
                if membership.theme_id in visible_ids
            )
            visible_metrics = AggregateThemeMetrics(
                all_themes=tuple(
                    metric
                    for metric in all_metrics.all_themes
                    if metric.theme_id in visible_ids
                ),
                positive_headlines=all_metrics.positive_headlines,
                negative_headlines=all_metrics.negative_headlines,
            )
            report = AggregateReport(
                schema_version="3.0",
                report_id=report_id,
                kind="test",
                app_id=run.app_id,
                metadata_snapshot=metadata,
                review_revision_ids=run.review_revision_ids,
                oldest_review_revision_ids=run.early_review_revision_ids,
                newest_review_revision_ids=run.recent_review_revision_ids,
                oversized_review_count=run.oversized_review_count,
                provider=run.provider,
                model=run.model,
                contract_version=ANALYSIS_CONTRACT_VERSION,
                metric_policy=run.metric_policy,
                themes=visible_themes,
                memberships=visible_memberships,
                theme_metrics=visible_metrics,
            )
            save_aggregate_report(self._database_path, report)
            finish_analysis_run(
                self._database_path,
                run.id,
                "completed",
                report_version_id=report_id,
                input_tokens=provider_run.usage.input_tokens,
                cached_input_tokens=provider_run.usage.cached_input_tokens,
                output_tokens=provider_run.usage.output_tokens,
            )
            log_event(
                "analysis.completed",
                run_id=run.id,
                duration_ms=round((monotonic() - started_at) * 1000),
                theme_count=len(visible_themes),
            )
        except AnalysisProviderError as error:
            state = "cancelled" if error.code == "cancelled" else "failed"
            finish_analysis_run(self._database_path, run.id, state, error_code=error.code)
            log_event(
                f"analysis.{state}",
                level="error" if state == "failed" else "info",
                run_id=run.id,
                report_kind="test",
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code=error.code,
                error_type=type(error).__name__,
            )
        except ValueError as error:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="invalid_theme_result"
            )
            log_event(
                "analysis.failed",
                level="error",
                run_id=run.id,
                report_kind="test",
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code="invalid_theme_result",
                error_type=type(error).__name__,
            )
        except Exception as error:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="internal_analysis_error"
            )
            log_event(
                "analysis.failed",
                level="error",
                run_id=run.id,
                report_kind="test",
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code="internal_analysis_error",
                error_type=type(error).__name__,
            )

    def _analysis_provider(self) -> AnalysisProvider:
        if not isinstance(self._provider, AnalysisProvider):
            raise AnalysisProviderError(
                "provider_capability_mismatch",
                "Provider does not support Version 2 analysis",
            )
        return self._provider

    def _theme_provider(self) -> ThemeAnalysisProvider:
        if not isinstance(self._provider, ThemeAnalysisProvider):
            raise AnalysisProviderError(
                "provider_capability_mismatch",
                "Provider does not support Version 3 Theme analysis",
            )
        return self._provider

    def _theme_merge_provider(self) -> ThemeMergeProvider:
        if not isinstance(self._provider, ThemeMergeProvider):
            raise AnalysisProviderError(
                "provider_capability_mismatch",
                "Provider does not support Version 3 Theme merging",
            )
        return self._provider

    def _batches(
        self,
        revision_ids: tuple[int, ...],
        revisions: dict[int, SteamReview],
    ) -> Iterator[tuple[int, ...]]:
        yield from pack_review_batches(
            revision_ids,
            revisions,
            min(self._batch_character_limit, 32_000),
            self._batch_review_limit,
        )


def _sum_usage(
    usages: tuple[ProviderUsage, ...],
    field: str,
) -> int | None:
    values: tuple[int, ...] = tuple(
        value
        for usage in usages
        if (value := getattr(usage, field)) is not None
    )
    return sum(values) if values else None
