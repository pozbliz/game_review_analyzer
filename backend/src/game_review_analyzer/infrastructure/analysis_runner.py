"""Durable provider analysis-to-report runner."""

from pathlib import Path
from typing import Protocol

from game_review_analyzer.application.manual_codex import build_analysis_request
from game_review_analyzer.application.report_creation import create_report
from game_review_analyzer.domain.analysis import AnalysisRequest, AnalysisSourceReview
from game_review_analyzer.infrastructure.codex_cli import CodexCliError, CodexCliRun
from game_review_analyzer.infrastructure.persistence.analysis_runs import (
    finish_analysis_run,
    get_analysis_run,
    start_analysis_run,
)
from game_review_analyzer.infrastructure.persistence.game_datasets import load_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import load_report_version
from game_review_analyzer.infrastructure.persistence.review_revisions import load_review_revisions_by_ids


class AnalysisProvider(Protocol):
    """Describe the provider behavior required by the durable runner."""

    model: str

    def analyze(self, request: AnalysisRequest, *, cancel_event: object) -> CodexCliRun:
        """Return one validated analysis result."""


class _DurableCancellation:
    def __init__(self, database_path: Path, run_id: str) -> None:
        self._database_path = database_path
        self._run_id = run_id

    def is_set(self) -> bool:
        return get_analysis_run(self._database_path, self._run_id).cancel_requested


class AnalysisRunner:
    """Run one queued provider analysis and persist its immutable report."""

    def __init__(self, database_path: Path, provider: AnalysisProvider) -> None:
        self._database_path = database_path
        self._provider = provider

    def run(self, run_id: str) -> None:
        run = start_analysis_run(self._database_path, run_id)
        if run is None:
            return
        report_id = f"analysis-{run.id}"
        if load_report_version(self._database_path, report_id) is not None:
            finish_analysis_run(
                self._database_path, run.id, "completed", report_version_id=report_id
            )
            return
        try:
            metadata = load_game_dataset(self._database_path, run.app_id)
            if metadata is None:
                raise ValueError("Matching Game Dataset metadata is unavailable")
            revisions = load_review_revisions_by_ids(
                self._database_path, run.review_revision_ids
            )
            request = build_analysis_request(
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
            provider_run = self._provider.analyze(
                request,
                cancel_event=cancellation,
            )
            if cancellation.is_set():
                finish_analysis_run(self._database_path, run.id, "cancelled")
                return
            if (
                provider_run.result.provider != run.provider
                or provider_run.result.model != run.model
            ):
                raise ValueError("Provider result provenance does not match the run")
            create_report(
                self._database_path,
                report_id,
                request,
                provider_run.result,
                run.review_revision_ids,
                run.metric_policy,
            )
            finish_analysis_run(
                self._database_path,
                run.id,
                "completed",
                report_version_id=report_id,
                input_tokens=provider_run.usage.input_tokens,
                cached_input_tokens=provider_run.usage.cached_input_tokens,
                output_tokens=provider_run.usage.output_tokens,
            )
        except CodexCliError as error:
            state = "cancelled" if error.code == "cancelled" else "failed"
            finish_analysis_run(self._database_path, run.id, state, error_code=error.code)
        except ValueError:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="invalid_analysis_scope"
            )
