"""Durable Codex CLI analysis-to-report integration tests."""

from pathlib import Path

from game_review_analyzer.domain.analysis import AnalysisResult, AnalysisSourceReview
from game_review_analyzer.domain.reports import ThemeMetricPolicy
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.analysis_runner import AnalysisRunner
from game_review_analyzer.infrastructure.codex_cli import CodexCliRun, CodexCliUsage
from game_review_analyzer.infrastructure.codex_cli import CodexCliStatus
from game_review_analyzer.infrastructure.ollama import OllamaModel, OllamaStatus
from game_review_analyzer.infrastructure.persistence.analysis_runs import (
    create_analysis_run,
    get_analysis_run,
)
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import load_report_version
from game_review_analyzer.infrastructure.persistence.review_revisions import save_review_revisions
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from fastapi.testclient import TestClient


class FakeProvider:
    """Return a valid empty result for the exact requested corpus."""

    model = "gpt-5.6-luna"
    provider = "codex-cli"

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


def test_run_snapshots_corpus_and_creates_immutable_report(tmp_path: Path) -> None:
    database_path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(database_path, metadata())
    save_review_revisions(database_path, 1145350, (review("First version", 100),))
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

    AnalysisRunner(database_path, FakeProvider()).run(run.id)

    completed = get_analysis_run(database_path, run.id)
    report = load_report_version(database_path, completed.report_version_id or "")
    assert completed.state == "completed"
    assert completed.review_count == 1
    assert completed.input_tokens == 120
    assert completed.cached_input_tokens == 20
    assert completed.output_tokens == 30
    assert report is not None
    assert report.analysis_result.provider == "codex-cli"
    assert report.review_revision_ids == run.review_revision_ids


def test_api_starts_and_exposes_completed_codex_analysis(tmp_path: Path) -> None:
    database_path = tmp_path / "app.sqlite3"
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", "gpt-5.6-luna", "medium"
    )
    with TestClient(
        create_app(
            Settings(database_path=database_path),
            codex_status_source=status,
            analysis_provider=FakeProvider(),
        )
    ) as client:
        save_game_dataset(database_path, metadata())
        save_review_revisions(database_path, 1145350, (review("Good game", 100),))
        started = client.post(
            "/api/games/1145350/analyses/codex-cli",
            json={
                "minimum_support_count": 2,
                "minimum_support_percentage": 1,
                "technical_minimum_support_count": 2,
                "technical_minimum_support_percentage": 1,
            },
        )
        run_id = started.json()["id"]
        completed = client.get(f"/api/analysis-runs/{run_id}")
        for _ in range(100):
            if completed.json()["state"] == "completed":
                break
            completed = client.get(f"/api/analysis-runs/{run_id}")

    assert started.status_code == 202
    assert completed.json()["review_count"] == 1
    assert completed.json()["report_version_id"] is not None


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
    database_path = tmp_path / "app.sqlite3"
    status = OllamaStatus(
        True,
        "0.12.6",
        (OllamaModel("qwen3.5:4b", 3_400_000_000, "4B", "Q4_K_M"),),
    )
    provider = FakeProvider()
    provider.provider = "ollama"
    provider.model = "qwen3.5:4b"
    with TestClient(create_app(
        Settings(database_path=database_path),
        ollama_status_source=lambda: status,
        analysis_provider=provider,
    )) as client:
        save_game_dataset(database_path, metadata())
        save_review_revisions(database_path, 1145350, (review("Good game", 100),))
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
