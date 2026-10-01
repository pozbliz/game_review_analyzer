"""First Main Report integration tests."""

from pathlib import Path

from game_review_analyzer.application.provider import (
    AnalysisProviderError,
    ProviderUsage,
    ThemeMergeProviderRun,
    ThemeProviderRun,
)
from game_review_analyzer.domain.analysis import (
    ANALYSIS_CONTRACT_VERSION,
    ThemeAnalysisResult,
    ThemeCandidate,
    ThemeMergeAssignment,
    ThemeMergeResult,
    ThemeMergeTheme,
)
from game_review_analyzer.domain.reports import ThemeMetricPolicy
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.analysis_runs import (
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
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
    save_review_revisions,
)
from game_review_analyzer.infrastructure.analysis_runner import AnalysisRunner
from game_review_analyzer.infrastructure.codex_cli import CodexCliStatus
from game_review_analyzer.infrastructure.persistence.report_versions import (
    load_aggregate_report_slot,
    save_aggregate_report,
)
from game_review_analyzer.infrastructure.persistence.theme_batches import (
    load_theme_batch,
    save_theme_batch,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from fastapi.testclient import TestClient


def test_main_report_selects_500_oldest_and_500_newest_complete_reviews(
    tmp_path: Path,
) -> None:
    database_path: Path = seeded_database(
        tmp_path,
        review_count=2_000,
        oversized=(1, 1_000),
    )

    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        cohort_size=500,
        report_kind="main",
    )

    reviews: dict[int, SteamReview] = load_review_revisions_by_ids(
        database_path, run.review_revision_ids
    )
    oldest_times: list[int] = [
        reviews[revision_id].source_created_at
        for revision_id in run.early_review_revision_ids
    ]
    newest_times: list[int] = [
        reviews[revision_id].source_created_at
        for revision_id in run.recent_review_revision_ids
    ]
    assert len(run.early_review_revision_ids) == 500
    assert len(run.recent_review_revision_ids) == 500
    assert run.oversized_review_count == 1
    assert set(run.early_review_revision_ids).isdisjoint(run.recent_review_revision_ids)
    assert oldest_times == list(range(2, 502))
    assert newest_times == list(range(1_501, 2_001))
    assert reviews[run.early_review_revision_ids[0]].text == "Review 2"


def test_main_report_reuses_map_checkpoints_and_retains_two_percent_candidates(
    tmp_path: Path,
) -> None:
    class CheckpointingProvider:
        model: str = "gpt-5.6-luna"
        provider: str = "codex-cli"

        def __init__(self) -> None:
            self.map_calls: int = 0
            self.failed_once: bool = False

        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            self.map_calls += 1
            if self.map_calls == 2 and not self.failed_once:
                self.failed_once = True
                raise AnalysisProviderError("provider_nonzero_exit", "test failure")
            themes: tuple[ThemeCandidate, ...] = ()
            if request.request_id.endswith("map-1"):
                ids: tuple[str, ...] = tuple(
                    review.review_revision_id for review in request.reviews
                )
                themes = (
                    candidate("visible", ids[:25]),
                    candidate("retained", ids[25:35]),
                    candidate("small", ids[35:44]),
                    candidate("discarded", ids[44:45]),
                )
            return ThemeProviderRun(
                result=ThemeAnalysisResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    completed_review_revision_ids=tuple(
                        review.review_revision_id for review in request.reviews
                    ),
                    themes=themes,
                ),
                usage=ProviderUsage(100, 0, 10),
            )

        def merge_themes(self, request, *, cancel_event=None) -> ThemeMergeProviderRun:
            by_title = {item.title: item.candidate_key for item in request.candidates}
            return ThemeMergeProviderRun(
                result=ThemeMergeResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    themes=tuple(
                        ThemeMergeTheme(
                            theme_id=title,
                            title=title.title(),
                            summary=f"{title.title()} summary.",
                            polarity="positive",
                        )
                        for title in ("visible", "retained", "small")
                    ),
                    assignments=tuple(
                        ThemeMergeAssignment(
                            candidate_key=by_title[title],
                            theme_id=title,
                        )
                        for title in ("visible", "retained", "small")
                    ) + (ThemeMergeAssignment(
                        candidate_key=by_title["discarded"],
                        theme_id=None,
                    ),),
                ),
                usage=ProviderUsage(50, 0, 5),
            )

    database_path: Path = seeded_database(tmp_path, review_count=1_000)
    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        cohort_size=500,
        report_kind="main",
    )
    provider = CheckpointingProvider()

    AnalysisRunner(database_path, provider, batch_review_limit=250).run(run.id)
    assert get_analysis_run(database_path, run.id).state == "failed"

    retry_analysis_run(database_path, run.id)
    AnalysisRunner(database_path, provider, batch_review_limit=250).run(run.id)

    completed = get_analysis_run(database_path, run.id)
    report = load_aggregate_report_slot(database_path, 1145350, "main")
    assert provider.map_calls == 5
    assert completed.state == "completed"
    assert completed.input_tokens == 450
    assert report is not None
    assert {theme.theme_id for theme in report.themes} == {"visible", "retained"}
    assert tuple(
        metric.theme_id for metric in report.theme_metrics.positive_headlines
    ) == ("visible",)
    with TestClient(
        create_app(
            Settings(database_path=database_path),
            analysis_provider=provider,
        )
    ) as client:
        visible_evidence = client.get(
            "/api/games/1145350/reports/main/themes/visible/evidence"
        )
        retained_evidence = client.get(
            "/api/games/1145350/reports/main/themes/retained/evidence"
        )
    assert visible_evidence.status_code == 200
    assert retained_evidence.status_code == 404


def test_theme_batch_from_previous_contract_is_ignored(tmp_path: Path) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=2)
    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
    )
    provider_run = ThemeProviderRun(
        result=ThemeAnalysisResult(
            schema_version="3.1",
            request_id="old-map",
            scope_sha256="a" * 64,
            provider="codex-cli",
            model="gpt-5.6-luna",
            completed_review_revision_ids=("review-1",),
            themes=(),
        ),
        usage=ProviderUsage(10, 0, 2),
    )
    save_theme_batch(
        database_path,
        run_id=run.id,
        batch_number=1,
        input_digest="a" * 64,
        provider="codex-cli",
        model="gpt-5.6-luna",
        contract_version="3.0",
        provider_run=provider_run,
    )

    loaded = load_theme_batch(
        database_path,
        run_id=run.id,
        batch_number=1,
        input_digest="a" * 64,
        provider="codex-cli",
        model="gpt-5.6-luna",
        contract_version=ANALYSIS_CONTRACT_VERSION,
    )

    assert loaded is None


def test_api_creates_and_reads_the_first_main_report(tmp_path: Path) -> None:
    class EmptyThemeProvider:
        model: str = "gpt-5.6-luna"
        provider: str = "codex-cli"

        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            return ThemeProviderRun(
                result=ThemeAnalysisResult(
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
                usage=ProviderUsage(100, 0, 10),
            )

    database_path: Path = seeded_database(tmp_path, review_count=100)
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", "gpt-5.6-luna", "low"
    )
    with TestClient(
        create_app(
            Settings(database_path=database_path),
            codex_status_source=status,
            analysis_provider=EmptyThemeProvider(),
        )
    ) as client:
        started = client.post(
            "/api/games/1145350/reports/main",
            json={
                "minimum_support_percentage": 7.5,
                "maximum_headlines_per_polarity": 4,
            },
        )
        run_id: str = started.json()["id"]
        completed = client.get(f"/api/analysis-runs/{run_id}")
        for _ in range(100):
            if completed.json()["state"] == "completed":
                break
            completed = client.get(f"/api/analysis-runs/{run_id}")
        report = client.get("/api/games/1145350/reports/main")
        replacement = client.post("/api/games/1145350/reports/main")
        pending_report = client.get("/api/games/1145350/reports/main").json()
        replaced = wait_for_completion(client, replacement.json()["id"])
        replacement_report = client.get("/api/games/1145350/reports/main").json()
        workspace = client.get("/api/games/1145350/workspace")

    assert started.status_code == 202
    assert started.json()["report_kind"] == "main"
    assert started.json()["review_count"] == 100
    assert started.json()["metric_policy"]["minimum_support_percentage"] == 7.5
    assert started.json()["metric_policy"]["maximum_headlines_per_polarity"] == 4
    assert completed.json()["state"] == "completed"
    assert completed.json()["extracted_review_count"] == 100
    assert report.status_code == 200
    assert report.json()["kind"] == "main"
    assert report.json()["scope"] == {
        "review_count": 100,
        "oldest_review_count": 50,
        "newest_review_count": 50,
        "oversized_review_count": 0,
    }
    assert report.json()["positive_themes"] == []
    assert report.json()["negative_themes"] == []
    assert replacement.status_code == 202
    assert pending_report["report_id"] == report.json()["report_id"]
    assert replaced["state"] == "completed"
    assert replacement_report["report_id"] != report.json()["report_id"]
    assert replacement_report["scope"]["review_count"] == 100
    assert workspace.json()["main_report_available"] is True


def test_api_extends_main_report_with_1000_unseen_reviews(tmp_path: Path) -> None:
    class EmptyThemeProvider:
        model: str = "gpt-5.6-luna"
        provider: str = "codex-cli"

        def __init__(self) -> None:
            self.invalid: bool = False

        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            return ThemeProviderRun(
                result=ThemeAnalysisResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    completed_review_revision_ids=tuple(
                        review.review_revision_id for review in request.reviews
                    ) if not self.invalid else ("wrong-review",),
                    themes=(),
                ),
                usage=ProviderUsage(100, 0, 10),
            )

    database_path: Path = seeded_database(tmp_path, review_count=3_000)
    provider = EmptyThemeProvider()
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", "gpt-5.6-luna", "low"
    )
    with TestClient(create_app(
        Settings(database_path=database_path),
        codex_status_source=status,
        analysis_provider=provider,
    )) as client:
        initial = client.post(
            "/api/games/1145350/reports/main",
            json={
                "minimum_support_percentage": 7.5,
                "maximum_headlines_per_polarity": 4,
            },
        )
        wait_for_completion(client, initial.json()["id"])
        first_report = client.get("/api/games/1145350/reports/main").json()
        stored_report = load_aggregate_report_slot(database_path, 1145350, "main")
        assert stored_report is not None
        save_aggregate_report(
            database_path,
            stored_report.model_copy(update={"contract_version": "3.0"}),
        )

        extension = client.post("/api/games/1145350/reports/main/extend")
        pending_report = client.get("/api/games/1145350/reports/main").json()
        completed = wait_for_completion(client, extension.json()["id"])
        extended_report = client.get("/api/games/1145350/reports/main").json()

        provider.invalid = True
        invalid_extension = client.post("/api/games/1145350/reports/main/extend")
        failed = wait_for_completion(client, invalid_extension.json()["id"])
        retained_report = client.get("/api/games/1145350/reports/main").json()

    assert extension.status_code == 202
    assert extension.json()["review_count"] == 1_000
    assert extension.json()["metric_policy"]["minimum_support_percentage"] == 7.5
    assert extension.json()["metric_policy"]["maximum_headlines_per_polarity"] == 4
    assert pending_report["report_id"] == first_report["report_id"]
    assert completed["state"] == "completed"
    assert extended_report["scope"]["review_count"] == 2_000
    assert extended_report["created_at"]
    assert failed["state"] == "failed"
    assert retained_report["report_id"] == extended_report["report_id"]


def wait_for_completion(client: TestClient, run_id: str) -> dict:
    response = client.get(f"/api/analysis-runs/{run_id}")
    for _ in range(100):
        if response.json()["state"] == "completed":
            break
        response = client.get(f"/api/analysis-runs/{run_id}")
    return response.json()


def candidate(candidate_id: str, review_ids: tuple[str, ...]) -> ThemeCandidate:
    return ThemeCandidate(
        candidate_id=candidate_id,
        title=candidate_id,
        summary=f"{candidate_id.title()} summary.",
        polarity="positive",
        supporting_review_revision_ids=review_ids,
    )


def seeded_database(
    tmp_path: Path,
    *,
    review_count: int,
    oversized: int | tuple[int, ...] | None = None,
) -> Path:
    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_game_dataset(
        database_path,
        SteamMetadata(
            app_id=1145350,
            title="Hades II",
            developers=("Supergiant Games",),
            capsule_image_url=None,
            release_date=None,
            release_status="unknown",
            review_count=review_count,
            source_status="partial",
            missing_fields=frozenset(
                {"capsule_image_url", "release_date", "release_status"}
            ),
        ),
    )
    oversized_positions: set[int] = (
        set(oversized) if isinstance(oversized, tuple) else {oversized}
    ) if oversized is not None else set()
    reviews: tuple[SteamReview, ...] = tuple(
        SteamReview(
            review_id=f"review-{position:04d}",
            language="english",
            text="x" * 32_001 if position in oversized_positions else f"Review {position}",
            source_created_at=position,
            source_updated_at=position,
            recommended=True,
            votes_helpful=0,
            votes_funny=0,
            weighted_vote_score=0,
            steam_purchase=True,
            received_for_free=False,
            written_during_early_access=False,
            playtime_forever_minutes=60,
            playtime_at_review_minutes=60,
        )
        for position in range(1, review_count + 1)
    )
    save_review_revisions(database_path, 1145350, reviews)
    job = create_full_job(database_path, 1145350)
    start_job(database_path, job.id)
    finish_job(database_path, job.id, "completed")
    return database_path


def metric_policy() -> ThemeMetricPolicy:
    return ThemeMetricPolicy(
        minimum_support_count=1,
        minimum_support_percentage=5,
        technical_minimum_support_count=1,
        technical_minimum_support_percentage=5,
        maximum_headlines_per_polarity=5,
    )
