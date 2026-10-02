"""Durable provider analysis-to-report runner."""

from collections.abc import Iterator
from pathlib import Path
from time import monotonic
from typing import Protocol, runtime_checkable

from game_review_analyzer.application.main_report import pack_review_batches
from game_review_analyzer.application.provider import (
    AnalysisProviderError,
    build_theme_merge_request,
    build_theme_analysis_request,
    CancellationSignal,
    ThemeProviderRun,
    ThemeMergeProviderRun,
    ProviderUsage,
    validate_theme_merge_result,
    validate_theme_provider_result,
)
from game_review_analyzer.application.theme_metrics import calculate_aggregate_theme_metrics
from game_review_analyzer.domain.analysis import (
    AnalysisSourceReview,
    ANALYSIS_CONTRACT_VERSION,
    ThemeAnalysisRequest,
    ThemeMergeCandidate,
    ThemeMergeRequest,
    ThemeMergeTheme,
    ThemePolarity,
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
    NoUnseenReviews,
    fail_analysis_run,
    finish_analysis_run,
    get_analysis_run,
    reserve_refreshed_analysis_scope,
    start_analysis_run,
)
from game_review_analyzer.infrastructure.job_runner import JobRunner
from game_review_analyzer.infrastructure.persistence.jobs import get_job
from game_review_analyzer.infrastructure.persistence.game_datasets import load_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import (
    complete_aggregate_report_run,
    load_aggregate_report_slot,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
)
from game_review_analyzer.infrastructure.persistence.theme_batches import (
    load_theme_batch,
    save_theme_batch,
)
from game_review_analyzer.infrastructure.persistence.theme_merge_batches import (
    load_theme_merge_batch,
    save_theme_merge_batch,
)
from game_review_analyzer.shared.telemetry import TRACER, log_event


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
        provider: ThemeAnalysisProvider,
        *,
        refresh_runner: JobRunner | None = None,
        batch_review_limit: int = 50,
        batch_character_limit: int = 32_000,
        merge_candidate_limit: int = 25,
    ) -> None:
        if merge_candidate_limit <= 0:
            raise ValueError("merge_candidate_limit must be positive")
        self._database_path = database_path
        self._provider = provider
        self._refresh_runner = refresh_runner
        self._batch_review_limit = batch_review_limit
        self._batch_character_limit = batch_character_limit
        self._merge_candidate_limit = merge_candidate_limit

    def run(self, run_id: str) -> None:
        started_at: float = monotonic()
        run = start_analysis_run(self._database_path, run_id)
        if run is None:
            return
        if run.refresh_job_id is not None:
            if self._refresh_runner is None:
                finish_analysis_run(
                    self._database_path,
                    run.id,
                    "failed",
                    error_code="refresh_runner_unavailable",
                )
                return
            self._refresh_runner.run(run.refresh_job_id)
            refresh_job = get_job(self._database_path, run.refresh_job_id)
            if refresh_job.state != "completed":
                state = "cancelled" if refresh_job.state == "cancelled" else "failed"
                finish_analysis_run(
                    self._database_path,
                    run.id,
                    state,
                    error_code=refresh_job.error_code,
                )
                return
            try:
                run = reserve_refreshed_analysis_scope(self._database_path, run.id)
            except NoUnseenReviews:
                finish_analysis_run(
                    self._database_path,
                    run.id,
                    "failed",
                    error_code="no_unseen_reviews",
                )
                return
            except ValueError:
                finish_analysis_run(
                    self._database_path,
                    run.id,
                    "failed",
                    error_code="invalid_refresh_scope",
                )
                return
        try:
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
        except Exception:
            fail_analysis_run(self._database_path, run.id, "tracing_failed")

    def _run_started(self, run: AnalysisRun, started_at: float) -> None:
        if run.report_kind == "test":
            self._run_test_report(run, started_at)
            return
        if run.report_kind == "main":
            self._run_main_report(run, started_at)
            return
        finish_analysis_run(
            self._database_path,
            run.id,
            "failed",
            error_code="unsupported_report_kind",
        )
    def _run_main_report(self, run: AnalysisRun, started_at: float) -> None:
        report_id: str = f"analysis-{run.id}"
        try:
            current_report: AggregateReport | None = load_aggregate_report_slot(
                self._database_path, run.app_id, "main"
            )
        except Exception:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="database_failed"
            )
            return
        if current_report is not None and current_report.report_id == report_id:
            finish_analysis_run(
                self._database_path, run.id, "completed", report_version_id=report_id
            )
            return
        extension_report: AggregateReport | None = None
        if run.operation == "extend":
            if current_report is None or current_report.report_id != run.base_report_id:
                finish_analysis_run(
                    self._database_path,
                    run.id,
                    "failed",
                    error_code="base_report_changed",
                )
                return
            extension_report = current_report
        stage: str = "database"
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
            stage = "provider_execution"
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

            if cancellation.is_set():
                finish_analysis_run(self._database_path, run.id, "cancelled")
                return
            merge_usages: list[ProviderUsage] = []
            themes: tuple[ThemeDefinition, ...] = (
                extension_report.themes if extension_report is not None else ()
            )
            memberships: tuple[ThemeMembership, ...] = (
                extension_report.memberships if extension_report is not None else ()
            )
            if merge_candidates:
                candidate_by_key: dict[str, ThemeMergeCandidate] = {
                    candidate.candidate_key: candidate
                    for candidate in merge_candidates
                }
                revision_id_by_review_id: dict[str, int] = {
                    review.review_id: revision_id
                    for revision_id, review in revisions.items()
                }
                known_theme_ids: set[str] = {theme.theme_id for theme in themes}
                membership_pairs: set[tuple[str, int]] = set()
                for polarity in ThemePolarity:
                    polarity_candidates: tuple[ThemeMergeCandidate, ...] = tuple(
                        candidate
                        for candidate in merge_candidates
                        if candidate.polarity == polarity
                    )
                    for merge_batch_number, offset in enumerate(
                        range(0, len(polarity_candidates), self._merge_candidate_limit),
                        start=1,
                    ):
                        merge_request: ThemeMergeRequest = build_theme_merge_request(
                            request_id=(
                                f"{run.id}-merge-{polarity.value}-{merge_batch_number}"
                            ),
                            app_id=run.app_id,
                            game_title=metadata.title,
                            candidates=polarity_candidates[
                                offset : offset + self._merge_candidate_limit
                            ],
                            established_themes=(
                                ThemeMergeTheme(
                                    theme_id=theme.theme_id,
                                    title=theme.title,
                                    summary=theme.summary,
                                    polarity=theme.polarity,
                                )
                                for theme in themes
                                if theme.polarity == polarity
                            ),
                        )
                        merge_run: ThemeMergeProviderRun | None = (
                            load_theme_merge_batch(
                                self._database_path,
                                run_id=run.id,
                                polarity=polarity.value,
                                batch_number=merge_batch_number,
                                request=merge_request,
                                provider=run.provider,
                                model=run.model,
                                contract_version=ANALYSIS_CONTRACT_VERSION,
                            )
                        )
                        if merge_run is None:
                            merge_run = self._theme_merge_provider().merge_themes(
                                merge_request,
                                cancel_event=cancellation,
                            )
                            validate_theme_merge_result(
                                merge_request,
                                merge_run.result,
                                expected_provider=run.provider,
                                expected_model=run.model,
                            )
                            save_theme_merge_batch(
                                self._database_path,
                                run_id=run.id,
                                polarity=polarity.value,
                                batch_number=merge_batch_number,
                                request=merge_request,
                                provider=run.provider,
                                model=run.model,
                                contract_version=ANALYSIS_CONTRACT_VERSION,
                                provider_run=merge_run,
                            )
                        merge_usages.append(merge_run.usage)
                        for theme in merge_run.result.themes:
                            if theme.theme_id in known_theme_ids:
                                continue
                            themes += (ThemeDefinition(
                                theme_id=theme.theme_id,
                                title=theme.title,
                                summary=theme.summary,
                                polarity=theme.polarity,
                            ),)
                            known_theme_ids.add(theme.theme_id)
                        membership_pairs.update(
                            (
                                assignment.theme_id,
                                revision_id_by_review_id[review_id],
                            )
                            for assignment in merge_run.result.assignments
                            if assignment.theme_id is not None
                            for review_id in candidate_by_key[
                                assignment.candidate_key
                            ].supporting_review_revision_ids
                        )
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

            stage = "calculation"
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
            if cancellation.is_set():
                finish_analysis_run(self._database_path, run.id, "cancelled")
                return
            usages: tuple[ProviderUsage, ...] = tuple(
                provider_run.usage for provider_run in map_runs
            ) + tuple(merge_usages)
            stage = "persistence"
            completed: bool = complete_aggregate_report_run(
                self._database_path,
                run.id,
                report,
                input_tokens=_sum_usage(usages, "input_tokens"),
                cached_input_tokens=_sum_usage(usages, "cached_input_tokens"),
                output_tokens=_sum_usage(usages, "output_tokens"),
            )
            if not completed:
                return
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
            error_code: str = f"{stage}_failed"
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code=error_code
            )
            log_event(
                "analysis.failed",
                level="error",
                run_id=run.id,
                report_kind="main",
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code=error_code,
                error_type=type(error).__name__,
            )

    def _run_test_report(self, run: AnalysisRun, started_at: float) -> None:
        report_id: str = f"analysis-{run.id}"
        try:
            current_report: AggregateReport | None = load_aggregate_report_slot(
                self._database_path, run.app_id, "test"
            )
        except Exception:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="database_failed"
            )
            return
        if current_report is not None and current_report.report_id == report_id:
            finish_analysis_run(
                self._database_path, run.id, "completed", report_version_id=report_id
            )
            return
        stage: str = "database"
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
            cancellation = _DurableCancellation(self._database_path, run.id)
            stage = "provider_execution"
            provider_run: ThemeProviderRun = self._theme_provider().analyze_themes(
                request,
                cancel_event=cancellation,
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
            stage = "calculation"
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
            if cancellation.is_set():
                finish_analysis_run(self._database_path, run.id, "cancelled")
                return
            stage = "persistence"
            completed: bool = complete_aggregate_report_run(
                self._database_path,
                run.id,
                report,
                input_tokens=provider_run.usage.input_tokens,
                cached_input_tokens=provider_run.usage.cached_input_tokens,
                output_tokens=provider_run.usage.output_tokens,
            )
            if not completed:
                return
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
            error_code: str = f"{stage}_failed"
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code=error_code
            )
            log_event(
                "analysis.failed",
                level="error",
                run_id=run.id,
                report_kind="test",
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code=error_code,
                error_type=type(error).__name__,
            )

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
