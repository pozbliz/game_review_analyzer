"""Durable Codex CLI analysis-to-report integration tests."""

from pathlib import Path
from time import sleep

import pytest

from game_review_analyzer.application.provider import (
    ThemeProviderRun,
)
from game_review_analyzer.domain.analysis import (
    ThemeAnalysisResult,
    ThemeCandidate,
)
from game_review_analyzer.domain.reports import ThemeMetricPolicy
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.analysis_runner import AnalysisRunner
from game_review_analyzer.infrastructure.codex_cli import CodexCliUsage
from game_review_analyzer.infrastructure.codex_cli import CodexCliStatus
from game_review_analyzer.infrastructure.persistence.analysis_runs import (
    FullHistoryRequired,
    create_analysis_run,
    get_analysis_run,
)
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.jobs import (
    create_full_job,
    finish_job,
    start_job,
)
from game_review_analyzer.infrastructure.persistence.report_versions import (
    load_aggregate_report_slot,
)
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

    def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
        assert cancel_event is not None
        return ThemeProviderRun(
            ThemeAnalysisResult(
                schema_version="3.1",
                request_id=request.request_id,
                scope_sha256=request.scope_sha256,
                provider=self.provider,
                model=self.model,
                completed_review_revision_ids=tuple(
                    review.review_revision_id for review in request.reviews
                ),
                themes=(),
            ),
            CodexCliUsage(10, 0, 2),
        )


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
        provider="codex-cli",
        model="gpt-5.6-luna",
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


def test_test_report_uses_one_call_and_replaces_only_its_slot(tmp_path: Path) -> None:
    class ThemeProvider(FakeProvider):
        def __init__(self) -> None:
            self.calls: int = 0

        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            self.calls += 1
            supporting_ids: tuple[str, ...] = (
                request.reviews[0].review_revision_id,
                request.reviews[1].review_revision_id,
                request.reviews[-2].review_revision_id,
                request.reviews[-1].review_revision_id,
            )
            return ThemeProviderRun(
                ThemeAnalysisResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    completed_review_revision_ids=tuple(
                        review.review_revision_id for review in request.reviews
                    ),
                    themes=(
                        ThemeCandidate(
                            candidate_id="responsive-combat",
                            title="Responsive combat",
                            summary="Players praise responsive combat.",
                            polarity="positive",
                            supporting_review_revision_ids=supporting_ids,
                        ),
                    ),
                ),
                CodexCliUsage(100, 20, 30),
            )

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
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=ThemeMetricPolicy(
            minimum_support_count=2,
            minimum_support_percentage=1,
            technical_minimum_support_count=2,
            technical_minimum_support_percentage=1,
        ),
        cohort_size=25,
        report_kind="test",
    )
    provider = ThemeProvider()

    AnalysisRunner(database_path, provider).run(run.id)

    completed = get_analysis_run(database_path, run.id)
    report = load_aggregate_report_slot(database_path, 1145350, "test")
    assert provider.calls == 1
    assert completed.state == "completed"
    assert completed.review_count == 50
    assert completed.input_tokens == 100
    assert report is not None
    assert report.report_id == completed.report_version_id
    assert report.kind == "test"
    assert len(report.oldest_review_revision_ids) == 25
    assert len(report.newest_review_revision_ids) == 25
    assert report.theme_metrics.positive_headlines[0].support_count == 4
    assert load_aggregate_report_slot(database_path, 1145350, "main") is None


def test_invalid_theme_output_keeps_the_current_test_report(tmp_path: Path) -> None:
    class IncompleteThemeProvider(FakeProvider):
        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            return ThemeProviderRun(
                ThemeAnalysisResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    completed_review_revision_ids=tuple(
                        review.review_revision_id for review in request.reviews[:-1]
                    ),
                    themes=(),
                ),
                CodexCliUsage(10, 0, 2),
            )

    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(database_path, metadata())
    save_review_revisions(
        database_path,
        1145350,
        tuple(review_at(position) for position in range(1, 101)),
    )
    complete_full_import(database_path)
    first_run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=ThemeMetricPolicy(
            minimum_support_count=1,
            minimum_support_percentage=5,
            technical_minimum_support_count=1,
            technical_minimum_support_percentage=5,
        ),
        cohort_size=25,
        report_kind="test",
    )
    AnalysisRunner(database_path, FakeProvider()).run(first_run.id)
    current = load_aggregate_report_slot(database_path, 1145350, "test")
    assert current is not None

    failed_run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=ThemeMetricPolicy(
            minimum_support_count=1,
            minimum_support_percentage=5,
            technical_minimum_support_count=1,
            technical_minimum_support_percentage=5,
        ),
        cohort_size=25,
        report_kind="test",
    )
    AnalysisRunner(database_path, IncompleteThemeProvider()).run(failed_run.id)

    failed = get_analysis_run(database_path, failed_run.id)
    retained = load_aggregate_report_slot(database_path, 1145350, "test")
    assert failed.state == "failed"
    assert failed.error_code == "invalid_theme_result"
    assert retained is not None
    assert retained.report_id == current.report_id


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


def test_api_creates_and_reads_the_standalone_test_report(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    provider = FakeProvider()
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

        started = client.post("/api/games/1145350/reports/test")
        run_id: str = started.json()["id"]
        completed = client.get(f"/api/analysis-runs/{run_id}")
        for _ in range(100):
            if completed.json()["state"] == "completed":
                break
            completed = client.get(f"/api/analysis-runs/{run_id}")
        report = client.get("/api/games/1145350/reports/test")
        replacement_started = client.post("/api/games/1145350/reports/test")
        replacement_run_id: str = replacement_started.json()["id"]
        replacement_completed = client.get(
            f"/api/analysis-runs/{replacement_run_id}"
        )
        for _ in range(100):
            if replacement_completed.json()["state"] == "completed":
                break
            sleep(0.01)
            replacement_completed = client.get(
                f"/api/analysis-runs/{replacement_run_id}"
            )
        replacement_report = client.get("/api/games/1145350/reports/test")
        workspace = client.get("/api/games/1145350/workspace")

    assert started.status_code == 202
    assert started.json()["report_kind"] == "test"
    assert started.json()["review_count"] == 50
    assert completed.json()["state"] == "completed"
    assert report.status_code == 200
    assert report.json()["schema_version"] == "3.0"
    assert report.json()["kind"] == "test"
    assert "provider" not in report.json()
    assert "model" not in report.json()
    assert report.json()["scope"] == {
        "review_count": 50,
        "oldest_review_count": 25,
        "newest_review_count": 25,
        "oversized_review_count": 0,
    }
    assert report.json()["positive_themes"] == []
    assert report.json()["negative_themes"] == []
    assert replacement_completed.json()["state"] == "completed"
    assert replacement_report.json()["report_id"] != report.json()["report_id"]
    assert replacement_report.json()["report_id"] == (
        replacement_completed.json()["report_version_id"]
    )
    assert workspace.json()["test_report_available"] is True


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
