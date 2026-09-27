"""Durable Codex CLI analysis-to-report integration tests."""

import json
from pathlib import Path

import pytest

from game_review_analyzer.domain.analysis import AnalysisResult, AnalysisSourceReview
from game_review_analyzer.domain.reports import ThemeMetricPolicy
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.analysis_runner import AnalysisRunner
from game_review_analyzer.infrastructure.codex_cli import CodexCliRun, CodexCliUsage
from game_review_analyzer.infrastructure.codex_cli import CodexCliStatus
from game_review_analyzer.infrastructure.ollama import OllamaModel, OllamaStatus
from game_review_analyzer.infrastructure.persistence.analysis_runs import (
    FullHistoryRequired,
    create_analysis_run,
    get_analysis_run,
    retry_analysis_run,
)
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.jobs import (
    create_full_job,
    finish_job,
    start_job,
)
from game_review_analyzer.infrastructure.persistence.report_versions import load_report_version
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
    save_review_revisions,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from fastapi.testclient import TestClient


class FakeProvider:
    """Return a valid empty result for the exact requested corpus."""

    model = "gpt-5.6-luna"
    provider = "codex-cli"

    def extract(self, request, *, cancel_event=None):
        assert cancel_event is not None
        from game_review_analyzer.application.provider import ExtractionProviderRun
        from game_review_analyzer.domain.analysis import OpinionExtractionResult

        return ExtractionProviderRun(
            OpinionExtractionResult(
                schema_version="1.0",
                request_id=request.request_id,
                scope_sha256=request.scope_sha256,
                provider=self.provider,
                model=self.model,
                completed_review_revision_ids=tuple(
                    review.review_revision_id for review in request.reviews
                ),
                opinion_points=(),
            ),
            CodexCliUsage(10, 0, 2),
        )

    def analyze(self, request, *, cancel_event=None) -> CodexCliRun:
        assert cancel_event is not None
        result = AnalysisResult(
            schema_version="1.0",
            request_id=request.request_id,
            scope_sha256=request.scope_sha256,
            provider=self.provider,
            model=self.model,
            completed_review_revision_ids=tuple(
                review.review_revision_id for review in request.reviews
            ),
            opinion_points=(),
            themes=(),
            mechanic_classifications=(),
        )
        return CodexCliRun(result, CodexCliUsage(120, 20, 30))

    def consolidate(self, request, *, cancel_event=None) -> CodexCliRun:
        return self.analyze(request, cancel_event=cancel_event)


def test_analysis_scope_selects_non_overlapping_oldest_and_newest_reviews(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(database_path, metadata())
    reviews: tuple[SteamReview, ...] = tuple(
        review_at(position) for position in range(1, 5_003)
    )
    save_review_revisions(database_path, 1145350, reviews)
    complete_full_import(database_path)

    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=ThemeMetricPolicy(
            minimum_support_count=2,
            minimum_support_percentage=1,
            technical_minimum_support_count=2,
            technical_minimum_support_percentage=1,
        ),
    )

    assert run.review_count == 5_000
    assert len(run.early_review_revision_ids) == 2_500
    assert len(run.recent_review_revision_ids) == 2_500
    assert set(run.early_review_revision_ids).isdisjoint(run.recent_review_revision_ids)
    selected_reviews = load_review_revisions_by_ids(
        database_path, run.review_revision_ids
    )
    assert [
        selected_reviews[identifier].source_created_at
        for identifier in run.early_review_revision_ids
    ] == list(range(1, 2_501))
    assert [
        selected_reviews[identifier].source_created_at
        for identifier in run.recent_review_revision_ids
    ] == list(range(2_503, 5_003))


def test_analysis_scope_accepts_a_smaller_oldest_and_newest_pilot(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(database_path, metadata())
    save_review_revisions(
        database_path,
        1145350,
        tuple(review_at(position) for position in range(1, 101)),
    )
    complete_full_import(database_path)

    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="ollama",
        model="qwen3.5:4b",
        metric_policy=ThemeMetricPolicy(
            minimum_support_count=2,
            minimum_support_percentage=1,
            technical_minimum_support_count=2,
            technical_minimum_support_percentage=1,
        ),
        cohort_size=25,
    )

    selected_reviews = load_review_revisions_by_ids(
        database_path, run.review_revision_ids
    )
    assert run.review_count == 50
    assert [
        selected_reviews[identifier].source_created_at
        for identifier in run.early_review_revision_ids
    ] == list(range(1, 26))
    assert [
        selected_reviews[identifier].source_created_at
        for identifier in run.recent_review_revision_ids
    ] == list(range(76, 101))


def test_analysis_scope_requires_a_completed_full_history_import(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(database_path, metadata())
    save_review_revisions(database_path, 1145350, (review_at(1), review_at(2)))

    with pytest.raises(FullHistoryRequired):
        create_analysis_run(
            database_path,
            app_id=1145350,
            provider="codex-cli",
            model="gpt-5.6-luna",
            metric_policy=ThemeMetricPolicy(
                minimum_support_count=2,
                minimum_support_percentage=1,
                technical_minimum_support_count=2,
                technical_minimum_support_percentage=1,
            ),
        )


def test_failed_extraction_resumes_without_reprocessing_cached_reviews(
    tmp_path: Path,
) -> None:
    class FailsSecondBatch(FakeProvider):
        def __init__(self) -> None:
            self.calls: list[tuple[str, ...]] = []
            self.failed: bool = False

        def extract(self, request, *, cancel_event=None):
            identifiers: tuple[str, ...] = tuple(
                review.review_revision_id for review in request.reviews
            )
            self.calls.append(identifiers)
            if len(self.calls) == 2 and not self.failed:
                self.failed = True
                from game_review_analyzer.application.provider import AnalysisProviderError

                raise AnalysisProviderError("temporary", "temporary")
            return super().extract(request, cancel_event=cancel_event)

    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(database_path, metadata())
    save_review_revisions(
        database_path,
        1145350,
        tuple(review_at(position) for position in range(1, 6)),
    )
    complete_full_import(database_path)
    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=ThemeMetricPolicy(
            minimum_support_count=2,
            minimum_support_percentage=1,
            technical_minimum_support_count=2,
            technical_minimum_support_percentage=1,
        ),
    )
    provider = FailsSecondBatch()

    AnalysisRunner(database_path, provider, batch_review_limit=2).run(run.id)
    retry_analysis_run(database_path, run.id)
    AnalysisRunner(database_path, provider, batch_review_limit=2).run(run.id)

    assert get_analysis_run(database_path, run.id).state == "completed"
    assert provider.calls == [
        ("1", "2"),
        ("3", "4"),
        ("3", "4"),
        ("5",),
    ]


def test_run_snapshots_corpus_and_creates_immutable_report(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(database_path, metadata())
    save_review_revisions(database_path, 1145350, (review("First version", 100),))
    complete_full_import(database_path)
    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=ThemeMetricPolicy(
            minimum_support_count=2,
            minimum_support_percentage=1,
            technical_minimum_support_count=2,
            technical_minimum_support_percentage=1,
        ),
    )
    save_review_revisions(database_path, 1145350, (review("Changed later", 200),))

    caplog.set_level("INFO", logger="game_review_analyzer")
    AnalysisRunner(database_path, FakeProvider()).run(run.id)

    completed = get_analysis_run(database_path, run.id)
    report = load_report_version(database_path, completed.report_version_id or "")
    assert completed.state == "completed"
    assert completed.review_count == 1
    assert completed.input_tokens == 10
    assert completed.cached_input_tokens == 0
    assert completed.output_tokens == 2
    assert report is not None
    assert report.analysis_result.provider == "codex-cli"
    assert report.review_revision_ids == run.review_revision_ids
    events: list[dict[str, object]] = [
        json.loads(record.message) for record in caplog.records
    ]
    batch_event: dict[str, object] = next(
        event for event in events if event["event"] == "analysis.extraction_batch_completed"
    )
    assert batch_event["batch_number"] == 1
    assert batch_event["review_count"] == 1
    assert batch_event["provider_duration_ms"] >= 0
    assert batch_event["cache_duration_ms"] >= 0


def test_api_starts_and_exposes_completed_codex_analysis(tmp_path: Path) -> None:
    class BatchRecordingProvider(FakeProvider):
        def __init__(self) -> None:
            self.extraction_batch_sizes: list[int] = []

        def extract(self, request, *, cancel_event=None):
            self.extraction_batch_sizes.append(len(request.reviews))
            return super().extract(request, cancel_event=cancel_event)

    database_path = tmp_path / "app.sqlite3"
    provider = BatchRecordingProvider()
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", "gpt-5.6-luna", "low"
    )
    with TestClient(
        create_app(
            Settings(database_path=database_path),
            codex_status_source=status,
            analysis_provider=provider,
        )
    ) as client:
        save_game_dataset(database_path, metadata())
        save_review_revisions(
            database_path,
            1145350,
            tuple(review_at(position) for position in range(1, 101)),
        )
        complete_full_import(database_path)
        started = client.post(
            "/api/games/1145350/analyses/codex-cli",
            json={
                "cohort_size": 25,
                "minimum_support_count": 2,
                "minimum_support_percentage": 1,
                "technical_minimum_support_count": 2,
                "technical_minimum_support_percentage": 1,
            },
        )
        run_id = started.json()["id"]
        workspace = client.get("/api/games/1145350/workspace")
        completed = client.get(f"/api/analysis-runs/{run_id}")
        for _ in range(100):
            if completed.json()["state"] == "completed":
                break
            completed = client.get(f"/api/analysis-runs/{run_id}")

    assert started.status_code == 202
    assert started.json()["review_count"] == 50
    assert workspace.status_code == 200
    assert workspace.json()["full_history_ready"] is True
    assert workspace.json()["latest_analysis_run"]["id"] == run_id
    assert completed.json()["review_count"] == 50
    assert completed.json()["report_version_id"] is not None
    assert provider.extraction_batch_sizes == [10, 10, 10, 10, 10]


def test_api_rejects_analysis_when_codex_is_not_authenticated(tmp_path: Path) -> None:
    status = lambda: CodexCliStatus(
        True, False, "codex-cli test", "gpt-5.6-luna", "medium"
    )
    with TestClient(
        create_app(
            Settings(database_path=tmp_path / "app.sqlite3"),
            codex_status_source=status,
            analysis_provider=FakeProvider(),
        )
    ) as client:
        response = client.post(
            "/api/games/1145350/analyses/codex-cli",
            json={
                "minimum_support_count": 2,
                "minimum_support_percentage": 1,
                "technical_minimum_support_count": 2,
                "technical_minimum_support_percentage": 1,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "codex_cli_not_ready"


def test_api_runs_only_an_explicitly_installed_ollama_model(tmp_path: Path) -> None:
    class BatchRecordingProvider(FakeProvider):
        def __init__(self) -> None:
            self.extraction_batch_sizes: list[int] = []

        def extract(self, request, *, cancel_event=None):
            self.extraction_batch_sizes.append(len(request.reviews))
            return super().extract(request, cancel_event=cancel_event)

    database_path = tmp_path / "app.sqlite3"
    status = OllamaStatus(
        True,
        "0.12.6",
        (OllamaModel("qwen3.5:4b", 3_400_000_000, "4B", "Q4_K_M"),),
    )
    provider = BatchRecordingProvider()
    provider.provider = "ollama"
    provider.model = "qwen3.5:4b"
    with TestClient(create_app(
        Settings(database_path=database_path),
        ollama_status_source=lambda: status,
        analysis_provider=provider,
    )) as client:
        save_game_dataset(database_path, metadata())
        save_review_revisions(
            database_path,
            1145350,
            tuple(review_at(position) for position in range(1, 22)),
        )
        complete_full_import(database_path)
        started = client.post(
            "/api/games/1145350/analyses/ollama",
            json={
                "model": "qwen3.5:4b",
                "minimum_support_count": 2,
                "minimum_support_percentage": 1,
                "technical_minimum_support_count": 2,
                "technical_minimum_support_percentage": 1,
            },
        )
        missing = client.post(
            "/api/games/1145350/analyses/ollama",
            json={
                "model": "not-installed:latest",
                "minimum_support_count": 2,
                "minimum_support_percentage": 1,
                "technical_minimum_support_count": 2,
                "technical_minimum_support_percentage": 1,
            },
        )

    assert started.status_code == 202
    assert started.json()["provider"] == "ollama"
    assert started.json()["model"] == "qwen3.5:4b"
    assert provider.extraction_batch_sizes == [10, 10, 1]
    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "ollama_model_not_installed"


def metadata() -> SteamMetadata:
    return SteamMetadata(
        app_id=1145350,
        title="Hades II",
        developers=("Supergiant Games",),
        capsule_image_url=None,
        release_date=None,
        release_status="unknown",
        review_count=1,
        source_status="partial",
        missing_fields=frozenset({"capsule_image_url", "release_date", "release_status"}),
    )


def review(text: str, updated_at: int) -> SteamReview:
    return SteamReview(
        review_id="1001",
        language="english",
        text=text,
        source_created_at=100,
        source_updated_at=updated_at,
        recommended=True,
        votes_helpful=0,
        votes_funny=0,
        weighted_vote_score=0,
        steam_purchase=True,
        received_for_free=False,
        written_during_early_access=False,
        playtime_forever_minutes=10,
        playtime_at_review_minutes=10,
    )


def review_at(position: int) -> SteamReview:
    return review(f"Review {position}", position).model_copy(
        update={"review_id": str(position), "source_created_at": position}
    )


def complete_full_import(database_path: Path) -> None:
    job = create_full_job(database_path, 1145350)
    assert start_job(database_path, job.id) is not None
    finish_job(database_path, job.id, "completed")
