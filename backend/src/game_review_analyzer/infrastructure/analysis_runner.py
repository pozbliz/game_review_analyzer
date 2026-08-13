"""Durable provider analysis-to-report runner."""

import json
from collections.abc import Iterator
from pathlib import Path
from time import monotonic
from typing import Protocol

from game_review_analyzer.application.manual_codex import build_analysis_request
from game_review_analyzer.application.opinion_consolidation import (
    consolidate_opinion_points,
)
from game_review_analyzer.application.report_creation import create_report
from game_review_analyzer.application.provider import (
    AnalysisProviderError,
    CancellationSignal,
    ExtractionProviderRun,
    ProviderRun,
)
from game_review_analyzer.domain.analysis import AnalysisRequest, AnalysisSourceReview
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.infrastructure.persistence.analysis_runs import (
    AnalysisRun,
    finish_analysis_run,
    get_analysis_run,
    start_analysis_run,
)
from game_review_analyzer.infrastructure.persistence.game_datasets import load_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import load_report_version
from game_review_analyzer.infrastructure.persistence.opinion_extractions import (
    load_opinion_extractions,
    save_opinion_extraction_batch,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
)
from game_review_analyzer.shared.telemetry import TRACER, log_event


EXTRACTION_CONTRACT_VERSION = "1.0"


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
        provider: AnalysisProvider,
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
            cancellation = _DurableCancellation(self._database_path, run.id)
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
            input_tokens: int = 0
            cached_input_tokens: int = 0
            output_tokens: int = 0
            for batch_number, batch_revision_ids in enumerate(
                self._batches(pending_revision_ids, revisions), start=1
            ):
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
                    extraction = self._provider.extract(
                        batch_request, cancel_event=cancellation
                    )
                save_opinion_extraction_batch(
                    self._database_path,
                    revision_ids_by_review_id={
                        revisions[revision_id].review_id: revision_id
                        for revision_id in batch_revision_ids
                    },
                    result=extraction.result,
                    contract_version=EXTRACTION_CONTRACT_VERSION,
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
                                    for point in cached[revision_id]
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
                result = consolidate_opinion_points(
                    request,
                    tuple(
                        point
                        for revision_id in run.review_revision_ids
                        for point in cached[revision_id]
                    ),
                    provider=run.provider,
                    model=run.model,
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
                run_id=run.id,
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code=error.code,
            )
        except ValueError:
            finish_analysis_run(
                self._database_path, run.id, "failed", error_code="invalid_analysis_scope"
            )
            log_event(
                "analysis.failed",
                run_id=run.id,
                duration_ms=round((monotonic() - started_at) * 1000),
                error_code="invalid_analysis_scope",
            )

    def _batches(
        self,
        revision_ids: tuple[int, ...],
        revisions: dict[int, SteamReview],
    ) -> Iterator[tuple[int, ...]]:
        batch: list[int] = []
        characters: int = 0
        for revision_id in revision_ids:
            text_length: int = len(revisions[revision_id].text)
            if batch and (
                len(batch) >= self._batch_review_limit
                or characters + text_length > self._batch_character_limit
            ):
                yield tuple(batch)
                batch = []
                characters = 0
            batch.append(revision_id)
            characters += text_length
        if batch:
            yield tuple(batch)
