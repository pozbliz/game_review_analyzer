"""First Main Report integration tests."""

from pathlib import Path

import pytest
import game_review_analyzer.infrastructure.analysis_runner as analysis_runner_module
import game_review_analyzer.interfaces.http.app as http_app_module

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
    AnalysisReservationConflict,
    create_analysis_run,
    create_refresh_analysis_run,
    get_analysis_run,
    load_latest_analysis_run,
    recoverable_analysis_run_ids,
    reserve_refreshed_analysis_scope,
    request_analysis_cancellation,
    retry_analysis_run,
    start_analysis_run,
)
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.jobs import (
    connect,
    create_full_job,
    finish_job,
    get_job,
    recoverable_job_ids,
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
from game_review_analyzer.infrastructure.steam_reviews import (
    ReviewPage,
    SteamReviewsUnavailable,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from fastapi.testclient import TestClient


def test_refresh_analysis_run_exposes_measured_refresh_progress(tmp_path: Path) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=10)
    run = create_refresh_analysis_run(
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
        operation="replace",
        base_report_id="main-report",
    )
    assert run.refresh_job_id is not None
    with connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_jobs SET imported_count = 1500 WHERE id = ?",
            (run.refresh_job_id,),
        )

    running = start_analysis_run(database_path, run.id)

    assert running is not None
    assert running.phase == "refreshing"
    assert running.refresh_imported_count == 1_500
    assert running.refresh_target_count == 5_000


def test_report_slots_reserve_persisted_run_intent_independently(
    tmp_path: Path,
) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=100)

    main_run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        cohort_size=25,
        report_kind="main",
        operation="create",
    )

    assert main_run.operation == "create"
    assert main_run.base_report_id is None
    assert main_run.review_count == 50
    with pytest.raises(AnalysisReservationConflict):
        create_analysis_run(
            database_path,
            app_id=1145350,
            provider="codex-cli",
            model="gpt-5.6-luna",
            metric_policy=metric_policy(),
            cohort_size=25,
            report_kind="main",
            operation="create",
        )

    test_run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        cohort_size=25,
        report_kind="test",
        operation="test",
    )
    assert test_run.operation == "test"

    request_analysis_cancellation(database_path, main_run.id)
    replacement = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        cohort_size=25,
        report_kind="main",
        operation="create",
    )
    assert replacement.operation == "create"
    assert replacement.base_report_id is None


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


def test_test_report_replaces_oversized_reviews(tmp_path: Path) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=60, oversized=1)

    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        cohort_size=25,
        report_kind="test",
        operation="test",
    )

    reviews = load_review_revisions_by_ids(database_path, run.review_revision_ids)
    assert run.review_count == 50
    assert run.oversized_review_count == 1
    assert 1 not in {review.source_created_at for review in reviews.values()}


def test_extension_selects_new_reviews_ignores_edits_and_allows_partial_scope(
    tmp_path: Path,
) -> None:
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
                usage=ProviderUsage(1, 0, 1),
            )

    database_path: Path = seeded_database(
        tmp_path,
        review_count=1_200,
        oversized=1_001,
    )
    first_revision = load_review_revisions_by_ids(database_path, (1,))[1]
    refreshed_reviews = (
        first_revision.model_copy(
            update={"text": "Edited review", "source_updated_at": 9_999}
        ),
        first_revision.model_copy(
            update={
                "review_id": "new-review-1",
                "text": "New review 1",
                "source_created_at": 2_001,
                "source_updated_at": 2_001,
            }
        ),
        first_revision.model_copy(
            update={
                "review_id": "new-review-2",
                "text": "New review 2",
                "source_created_at": 2_002,
                "source_updated_at": 2_002,
            }
        ),
    )

    class RefreshSource:
        def iter_pages(self, app_id: int, start_cursor: str = "*"):
            del app_id, start_cursor
            yield ReviewPage(reviews=refreshed_reviews, next_cursor="done")
            yield ReviewPage(reviews=(), next_cursor="done")

    selected_model: list[str] = ["gpt-5.6-luna"]
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", selected_model[0], "low"
    )
    with TestClient(create_app(
        Settings(database_path=database_path),
        codex_status_source=status,
        analysis_provider=EmptyThemeProvider(),
        review_source=RefreshSource(),
    )) as client:
        initial = client.post("/api/games/1145350/reports/main")
        wait_for_completion(client, initial.json()["id"])
        selected_model[0] = "gpt-new-default"
        extension = client.post("/api/games/1145350/reports/main/extend")
        completed = wait_for_completion(client, extension.json()["id"])

    selected = load_review_revisions_by_ids(
        database_path, tuple(completed["review_revision_ids"])
    )
    assert completed["review_count"] == 201
    assert completed["model"] == "gpt-5.6-luna"
    assert completed["oversized_review_count"] == 1
    assert {"new-review-1", "new-review-2"}.issubset(
        review.review_id for review in selected.values()
    )
    assert "review-0001" not in {review.review_id for review in selected.values()}


def test_extension_keeps_theme_definitions_deduplicates_and_promotes_candidates(
    tmp_path: Path,
) -> None:
    class ExtensionProvider:
        model: str = "gpt-5.6-luna"
        provider: str = "codex-cli"

        def __init__(self) -> None:
            self.initial_merged: bool = False

        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            ids = tuple(review.review_revision_id for review in request.reviews)
            themes = (
                candidate("shared-a", ids[:10]),
                candidate("shared-b", ids[:10]),
            )
            if self.initial_merged:
                themes += (candidate("promoted", ids[10:20]),)
            return ThemeProviderRun(
                result=ThemeAnalysisResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    completed_review_revision_ids=ids,
                    themes=themes,
                ),
                usage=ProviderUsage(1, 0, 1),
            )

        def merge_themes(self, request, *, cancel_event=None) -> ThemeMergeProviderRun:
            extending: bool = bool(request.established_themes)
            replacing: bool = self.initial_merged and not extending
            themes = tuple(request.established_themes)
            if extending:
                themes += (ThemeMergeTheme(
                    theme_id="promoted",
                    title="Promoted",
                    summary="Promoted summary.",
                    polarity="positive",
                ),)
            elif not replacing:
                themes = (ThemeMergeTheme(
                    theme_id="shared",
                    title="Original shared title",
                    summary="Original shared summary.",
                    polarity="positive",
                ),)
                self.initial_merged = True
            else:
                themes = (ThemeMergeTheme(
                    theme_id="replacement",
                    title="Replacement",
                    summary="Replacement summary.",
                    polarity="positive",
                ),)
            return ThemeMergeProviderRun(
                result=ThemeMergeResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    themes=themes,
                    assignments=tuple(
                        ThemeMergeAssignment(
                            candidate_key=item.candidate_key,
                            theme_id=(
                                "replacement" if replacing else
                                "promoted" if item.title == "promoted" else "shared"
                            ),
                        )
                        for item in request.candidates
                    ),
                ),
                usage=ProviderUsage(1, 0, 1),
            )

    class EmptyRefreshSource:
        def iter_pages(self, app_id: int, start_cursor: str = "*"):
            del app_id, start_cursor
            yield ReviewPage(reviews=(), next_cursor="done")

    database_path: Path = seeded_database(tmp_path, review_count=2_000)
    provider = ExtensionProvider()
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", "gpt-5.6-luna", "low"
    )
    with TestClient(create_app(
        Settings(database_path=database_path),
        codex_status_source=status,
        analysis_provider=provider,
        review_source=EmptyRefreshSource(),
    )) as client:
        initial = client.post("/api/games/1145350/reports/main")
        wait_for_completion(client, initial.json()["id"])
        extension = client.post("/api/games/1145350/reports/main/extend")
        wait_for_completion(client, extension.json()["id"])
        extended_report = load_aggregate_report_slot(database_path, 1145350, "main")
        replacement = client.post("/api/games/1145350/reports/main")
        wait_for_completion(client, replacement.json()["id"])

    assert extended_report is not None
    definitions = {theme.theme_id: theme for theme in extended_report.themes}
    membership_counts = {
        theme_id: sum(
            membership.theme_id == theme_id for membership in extended_report.memberships
        )
        for theme_id in definitions
    }
    metric_counts = {
        metric.theme_id: metric.support_count
        for metric in extended_report.theme_metrics.all_themes
    }
    assert definitions["shared"].title == "Original shared title"
    assert set(definitions) == {"shared", "promoted"}
    assert membership_counts == {"shared": 80, "promoted": 40}
    assert metric_counts == membership_counts
    replaced_report = load_aggregate_report_slot(database_path, 1145350, "main")
    assert replaced_report is not None
    assert {theme.theme_id for theme in replaced_report.themes} == {"replacement"}
    assert len(replaced_report.review_revision_ids) == 1_000


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
    with connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_theme_batches SET result_json = '{' "
            "WHERE run_id = ? AND batch_number = 1",
            (run.id,),
        )

    retry_analysis_run(database_path, run.id)
    AnalysisRunner(database_path, provider, batch_review_limit=250).run(run.id)

    completed = get_analysis_run(database_path, run.id)
    report = load_aggregate_report_slot(database_path, 1145350, "main")
    assert provider.map_calls == 6
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
    assert visible_evidence.json()["theme_id"] == "visible"
    assert len(visible_evidence.json()["reviews"]) == 25
    assert retained_evidence.status_code == 404


def test_main_report_merges_positive_and_negative_candidates_separately(
    tmp_path: Path,
) -> None:
    class MixedPolarityProvider:
        model: str = "gpt-5.6-luna"
        provider: str = "codex-cli"

        def __init__(self) -> None:
            self.merge_polarities: list[set[str]] = []

        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            review_ids: tuple[str, ...] = tuple(
                review.review_revision_id for review in request.reviews
            )
            return ThemeProviderRun(
                result=ThemeAnalysisResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    completed_review_revision_ids=review_ids,
                    themes=(
                        candidate("positive", review_ids[:1]),
                        ThemeCandidate(
                            candidate_id="negative",
                            title="negative",
                            summary="Negative summary.",
                            polarity="negative",
                            supporting_review_revision_ids=review_ids[1:],
                        ),
                    ),
                ),
                usage=ProviderUsage(100, 0, 10),
            )

        def merge_themes(self, request, *, cancel_event=None) -> ThemeMergeProviderRun:
            polarities: set[str] = {
                candidate.polarity.value for candidate in request.candidates
            }
            self.merge_polarities.append(polarities)
            polarity: str = next(iter(polarities))
            theme_id: str = f"theme-{polarity}"
            return ThemeMergeProviderRun(
                result=ThemeMergeResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    themes=(ThemeMergeTheme(
                        theme_id=theme_id,
                        title=f"{polarity.title()} Theme",
                        summary=f"{polarity.title()} summary.",
                        polarity=polarity,
                    ),),
                    assignments=tuple(
                        ThemeMergeAssignment(
                            candidate_key=item.candidate_key,
                            theme_id=theme_id,
                        )
                        for item in request.candidates
                    ),
                ),
                usage=ProviderUsage(50, 0, 5),
            )

    database_path: Path = seeded_database(tmp_path, review_count=2)
    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        report_kind="main",
    )
    provider = MixedPolarityProvider()

    AnalysisRunner(database_path, provider).run(run.id)

    report = load_aggregate_report_slot(database_path, 1145350, "main")
    assert provider.merge_polarities == [{"positive"}, {"negative"}]
    assert report is not None
    assert {theme.theme_id for theme in report.themes} == {
        "theme-positive",
        "theme-negative",
    }
    assert get_analysis_run(database_path, run.id).input_tokens == 200


def test_main_report_resumes_bounded_merge_chunks_from_checkpoints(
    tmp_path: Path,
) -> None:
    class ChunkedMergeProvider:
        model: str = "gpt-5.6-luna"
        provider: str = "codex-cli"

        def __init__(self) -> None:
            self.merge_calls: list[str] = []
            self.failed_once: bool = False

        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            review_ids: tuple[str, ...] = tuple(
                review.review_revision_id for review in request.reviews
            )
            return ThemeProviderRun(
                result=ThemeAnalysisResult(
                    schema_version=ANALYSIS_CONTRACT_VERSION,
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    completed_review_revision_ids=review_ids,
                    themes=tuple(
                        candidate(f"candidate-{index}", review_ids)
                        for index in range(5)
                    ),
                ),
                usage=ProviderUsage(10, 0, 1),
            )

        def merge_themes(self, request, *, cancel_event=None) -> ThemeMergeProviderRun:
            self.merge_calls.append(request.request_id)
            if request.request_id.endswith("positive-2") and not self.failed_once:
                self.failed_once = True
                raise AnalysisProviderError("provider_timeout", "test timeout")
            theme_id: str = f"{request.request_id}:result"
            return ThemeMergeProviderRun(
                result=ThemeMergeResult(
                    schema_version=ANALYSIS_CONTRACT_VERSION,
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    themes=(
                        *request.established_themes,
                        ThemeMergeTheme(
                            theme_id=theme_id,
                            title=theme_id,
                            summary=f"{theme_id} summary.",
                            polarity="positive",
                        ),
                    ),
                    assignments=tuple(
                        ThemeMergeAssignment(
                            candidate_key=item.candidate_key,
                            theme_id=theme_id,
                        )
                        for item in request.candidates
                    ),
                ),
                usage=ProviderUsage(20, 0, 2),
            )

    database_path: Path = seeded_database(tmp_path, review_count=2)
    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        report_kind="main",
    )
    provider = ChunkedMergeProvider()
    runner = AnalysisRunner(database_path, provider, merge_candidate_limit=3)

    runner.run(run.id)
    assert get_analysis_run(database_path, run.id).state == "failed"

    retry_analysis_run(database_path, run.id)
    runner.run(run.id)

    assert provider.merge_calls == [
        f"{run.id}-merge-positive-1",
        f"{run.id}-merge-positive-2",
        f"{run.id}-merge-positive-2",
    ]
    with connect(database_path) as connection:
        checkpoint_count: int = connection.execute(
            "SELECT COUNT(*) FROM analysis_theme_merge_batches WHERE run_id = ?",
            (run.id,),
        ).fetchone()[0]
    assert checkpoint_count == 2
    assert get_analysis_run(database_path, run.id).state == "completed"


@pytest.mark.parametrize("cancel_stage", ("map", "merge"))
def test_cancelled_main_report_never_replaces_the_report_slot(
    tmp_path: Path,
    cancel_stage: str,
) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=2)
    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        report_kind="main",
        operation="create",
    )

    class CancellingProvider:
        model: str = "gpt-5.6-luna"
        provider: str = "codex-cli"

        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            if cancel_stage == "map":
                request_analysis_cancellation(database_path, run.id)
            review_ids = tuple(
                review.review_revision_id for review in request.reviews
            )
            return ThemeProviderRun(
                result=ThemeAnalysisResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    completed_review_revision_ids=review_ids,
                    themes=(candidate("cancel-theme", review_ids),),
                ),
                usage=ProviderUsage(1, 0, 1),
            )

        def merge_themes(self, request, *, cancel_event=None) -> ThemeMergeProviderRun:
            request_analysis_cancellation(database_path, run.id)
            return ThemeMergeProviderRun(
                result=ThemeMergeResult(
                    schema_version="3.1",
                    request_id=request.request_id,
                    scope_sha256=request.scope_sha256,
                    provider=self.provider,
                    model=self.model,
                    themes=(ThemeMergeTheme(
                        theme_id="cancel-theme",
                        title="Cancel theme",
                        summary="Cancel summary.",
                        polarity="positive",
                    ),),
                    assignments=tuple(
                        ThemeMergeAssignment(
                            candidate_key=item.candidate_key,
                            theme_id="cancel-theme",
                        )
                        for item in request.candidates
                    ),
                ),
                usage=ProviderUsage(1, 0, 1),
            )

    AnalysisRunner(database_path, CancellingProvider()).run(run.id)

    assert get_analysis_run(database_path, run.id).state == "cancelled"
    assert load_aggregate_report_slot(database_path, 1145350, "main") is None


def test_cancelling_before_refresh_cancels_the_owned_job(tmp_path: Path) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=2)
    base_run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        report_kind="main",
        operation="create",
    )

    class EmptyProvider:
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
                usage=ProviderUsage(1, 0, 1),
            )

    AnalysisRunner(database_path, EmptyProvider()).run(base_run.id)
    report = load_aggregate_report_slot(database_path, 1145350, "main")
    assert report is not None
    replacement = create_refresh_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=report.metric_policy,
        operation="replace",
        base_report_id=report.report_id,
    )
    assert replacement.refresh_job_id is not None

    request_analysis_cancellation(database_path, replacement.id)

    assert get_analysis_run(database_path, replacement.id).state == "cancelled"
    assert get_job(database_path, replacement.refresh_job_id).state == "cancelled"
    assert load_aggregate_report_slot(
        database_path, 1145350, "main"
    ).report_id == report.report_id


@pytest.mark.parametrize(
    ("failure_stage", "expected_code"),
    (
        ("database", "database_failed"),
        ("provider", "provider_execution_failed"),
        ("calculation", "calculation_failed"),
        ("persistence", "persistence_failed"),
        ("tracing", "tracing_failed"),
    ),
)
def test_main_report_worker_records_stage_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
    expected_code: str,
) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=2)
    run = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        report_kind="main",
        operation="create",
    )

    class Provider:
        model: str = "gpt-5.6-luna"
        provider: str = "codex-cli"

        def analyze_themes(self, request, *, cancel_event=None) -> ThemeProviderRun:
            if failure_stage == "provider":
                raise RuntimeError("provider failed")
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
                usage=ProviderUsage(1, 0, 1),
            )

    def fail(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("stage failed")

    if failure_stage == "database":
        monkeypatch.setattr(analysis_runner_module, "load_aggregate_report_slot", fail)
    elif failure_stage == "calculation":
        monkeypatch.setattr(
            analysis_runner_module, "calculate_aggregate_theme_metrics", fail
        )
    elif failure_stage == "persistence":
        monkeypatch.setattr(analysis_runner_module, "complete_aggregate_report_run", fail)
    elif failure_stage == "tracing":
        class FailingTracer:
            start_as_current_span = staticmethod(fail)

        monkeypatch.setattr(analysis_runner_module, "TRACER", FailingTracer())

    AnalysisRunner(database_path, Provider()).run(run.id)

    failed = get_analysis_run(database_path, run.id)
    assert failed.state == "failed"
    assert failed.error_code == expected_code
    assert load_aggregate_report_slot(database_path, 1145350, "main") is None


def test_provider_setup_failure_finishes_the_accepted_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=2)

    def fail_provider(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("provider setup failed")

    monkeypatch.setattr(http_app_module, "CodexCliProvider", fail_provider)
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", "gpt-5.6-luna", "low"
    )
    with TestClient(create_app(
        Settings(database_path=database_path),
        codex_status_source=status,
    )) as client:
        started = client.post("/api/games/1145350/reports/main")
        failed = wait_for_terminal_state(client, started.json()["id"])

    assert failed["state"] == "failed"
    assert failed["error_code"] == "provider_setup_failed"


def test_dispatch_failure_finishes_the_reserved_run(tmp_path: Path) -> None:
    database_path: Path = seeded_database(tmp_path, review_count=2)
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", "gpt-5.6-luna", "low"
    )

    class FailingExecutor:
        def submit(self, *args, **kwargs):
            del args, kwargs
            raise RuntimeError("dispatch failed")

    with TestClient(create_app(
        Settings(database_path=database_path),
        codex_status_source=status,
    )) as client:
        client.app.state.analysis_executor = FailingExecutor()
        response = client.post("/api/games/1145350/reports/main")

    run = load_latest_analysis_run(database_path, 1145350)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "analysis_dispatch_failed"
    assert run is not None
    assert run.state == "failed"
    assert run.error_code == "dispatch_failed"


def test_restart_preserves_the_reserved_scope_and_valid_checkpoint(
    tmp_path: Path,
) -> None:
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
                usage=ProviderUsage(1, 0, 1),
            )

    database_path: Path = seeded_database(tmp_path, review_count=2_000)
    initial = create_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=metric_policy(),
        cohort_size=500,
        report_kind="main",
        operation="create",
    )
    AnalysisRunner(database_path, EmptyThemeProvider(), batch_review_limit=250).run(
        initial.id
    )
    report = load_aggregate_report_slot(database_path, 1145350, "main")
    assert report is not None
    extension = create_refresh_analysis_run(
        database_path,
        app_id=1145350,
        provider="codex-cli",
        model="gpt-5.6-luna",
        metric_policy=report.metric_policy,
        operation="extend",
        base_report_id=report.report_id,
    )
    assert extension.refresh_job_id is not None
    start_job(database_path, extension.refresh_job_id)
    finish_job(database_path, extension.refresh_job_id, "completed")
    old_revision = load_review_revisions_by_ids(database_path, (501,))[501]
    save_review_revisions(
        database_path,
        1145350,
        (old_revision.model_copy(update={
            "text": "Edited after refresh",
            "source_updated_at": 9_999,
        }),),
    )
    analysis_runner_module.start_analysis_run(database_path, extension.id)
    reserved = reserve_refreshed_analysis_scope(database_path, extension.id)
    provider_run = ThemeProviderRun(
        result=ThemeAnalysisResult(
            schema_version="3.1",
            request_id=f"{extension.id}-map-1",
            scope_sha256="a" * 64,
            provider="codex-cli",
            model="gpt-5.6-luna",
            completed_review_revision_ids=("review-0501",),
            themes=(),
        ),
        usage=ProviderUsage(1, 0, 1),
    )
    save_theme_batch(
        database_path,
        run_id=extension.id,
        batch_number=1,
        input_digest="a" * 64,
        provider="codex-cli",
        model="gpt-5.6-luna",
        contract_version=ANALYSIS_CONTRACT_VERSION,
        provider_run=provider_run,
    )

    assert recoverable_job_ids(database_path) == []
    assert recoverable_analysis_run_ids(database_path) == [extension.id]
    recovered = get_analysis_run(database_path, extension.id)
    checkpoint = load_theme_batch(
        database_path,
        run_id=extension.id,
        batch_number=1,
        input_digest="a" * 64,
        provider="codex-cli",
        model="gpt-5.6-luna",
        contract_version=ANALYSIS_CONTRACT_VERSION,
    )
    assert recovered.review_revision_ids == reserved.review_revision_ids
    assert 501 in recovered.review_revision_ids
    assert checkpoint is not None


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
    save_theme_batch(
        database_path,
        run_id=run.id,
        batch_number=1,
        input_digest="a" * 64,
        provider="codex-cli",
        model="gpt-5.6-luna",
        contract_version=ANALYSIS_CONTRACT_VERSION,
        provider_run=provider_run,
    )
    with connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_theme_batches SET result_json = '{' "
            "WHERE run_id = ? AND batch_number = 1",
            (run.id,),
        )

    assert load_theme_batch(
        database_path,
        run_id=run.id,
        batch_number=1,
        input_digest="a" * 64,
        provider="codex-cli",
        model="gpt-5.6-luna",
        contract_version=ANALYSIS_CONTRACT_VERSION,
    ) is None
    save_theme_batch(
        database_path,
        run_id=run.id,
        batch_number=1,
        input_digest="a" * 64,
        provider="codex-cli",
        model="gpt-5.6-luna",
        contract_version=ANALYSIS_CONTRACT_VERSION,
        provider_run=provider_run,
    )


def test_api_creates_and_reads_the_first_main_report(tmp_path: Path) -> None:
    class EmptyRefreshSource:
        def __init__(self) -> None:
            self.calls: int = 0

        def iter_pages(self, app_id: int, start_cursor: str = "*"):
            del app_id, start_cursor
            self.calls += 1
            if self.calls == 1:
                raise SteamReviewsUnavailable
            yield ReviewPage(reviews=(), next_cursor="done")

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
    refresh_source = EmptyRefreshSource()
    with TestClient(
        create_app(
            Settings(database_path=database_path),
            codex_status_source=status,
            analysis_provider=EmptyThemeProvider(),
            review_source=refresh_source,
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
        replacement_failed = wait_for_completion(client, replacement.json()["id"])
        failed_report = client.get("/api/games/1145350/reports/main").json()
        retry = client.post(
            f"/api/analysis-runs/{replacement.json()['id']}/retry"
        )
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
    assert "provider" not in report.json()
    assert "model" not in report.json()
    assert report.json()["scope"] == {
        "review_count": 100,
        "oldest_review_count": 50,
        "newest_review_count": 50,
        "oversized_review_count": 0,
    }
    assert report.json()["unseen_review_count"] == 0
    assert report.json()["positive_themes"] == []
    assert report.json()["negative_themes"] == []
    assert replacement.status_code == 202
    assert pending_report["report_id"] == report.json()["report_id"]
    assert replacement_failed["error_code"] == "steam_unavailable"
    assert failed_report["report_id"] == report.json()["report_id"]
    assert retry.status_code == 202
    assert replaced["state"] == "completed"
    assert replacement_report["report_id"] != report.json()["report_id"]
    assert replacement_report["scope"]["review_count"] == 100
    assert workspace.json()["main_report_available"] is True
    assert refresh_source.calls == 2


def test_api_extends_main_report_with_1000_unseen_reviews(tmp_path: Path) -> None:
    class EmptyRefreshSource:
        def __init__(self) -> None:
            self.calls: int = 0
            self.fail: bool = False

        def iter_pages(self, app_id: int, start_cursor: str = "*"):
            del app_id, start_cursor
            self.calls += 1
            if self.fail:
                raise SteamReviewsUnavailable
            yield ReviewPage(reviews=(), next_cursor="done")

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

    database_path: Path = seeded_database(tmp_path, review_count=2_375)
    provider = EmptyThemeProvider()
    refresh_source = EmptyRefreshSource()
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", "gpt-5.6-luna", "low"
    )
    with TestClient(create_app(
        Settings(database_path=database_path),
        codex_status_source=status,
        analysis_provider=provider,
        review_source=refresh_source,
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

        refresh_source.fail = True
        refresh_failure = client.post("/api/games/1145350/reports/main/extend")
        refresh_failed = wait_for_completion(client, refresh_failure.json()["id"])
        report_after_refresh_failure = client.get(
            "/api/games/1145350/reports/main"
        ).json()
        refresh_source.fail = False
        provider.invalid = True
        invalid_extension = client.post("/api/games/1145350/reports/main/extend")
        failed = wait_for_completion(client, invalid_extension.json()["id"])
        retained_report = client.get("/api/games/1145350/reports/main").json()

    assert extension.status_code == 202
    assert extension.json()["review_count"] == 0
    assert completed["review_count"] == 1_000
    assert extension.json()["metric_policy"]["minimum_support_percentage"] == 7.5
    assert extension.json()["metric_policy"]["maximum_headlines_per_polarity"] == 4
    assert pending_report["report_id"] == first_report["report_id"]
    assert completed["state"] == "completed"
    assert extended_report["scope"]["review_count"] == 2_000
    assert extended_report["unseen_review_count"] == 375
    assert extended_report["created_at"]
    assert refresh_failed["state"] == "failed"
    assert refresh_failed["error_code"] == "steam_unavailable"
    assert report_after_refresh_failure["report_id"] == extended_report["report_id"]
    assert failed["state"] == "failed"
    assert retained_report["report_id"] == extended_report["report_id"]
    assert refresh_source.calls == 3


def test_extension_reports_when_no_unseen_reviews_remain(tmp_path: Path) -> None:
    class EmptyRefreshSource:
        def iter_pages(self, app_id: int, start_cursor: str = "*"):
            del app_id, start_cursor
            yield ReviewPage(reviews=(), next_cursor="done")

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
                usage=ProviderUsage(1, 0, 1),
            )

    database_path: Path = seeded_database(tmp_path, review_count=2)
    status = lambda: CodexCliStatus(
        True, True, "codex-cli test", "gpt-5.6-luna", "low"
    )
    with TestClient(create_app(
        Settings(database_path=database_path),
        codex_status_source=status,
        analysis_provider=EmptyThemeProvider(),
        review_source=EmptyRefreshSource(),
    )) as client:
        initial = client.post("/api/games/1145350/reports/main")
        wait_for_completion(client, initial.json()["id"])
        report_before = client.get("/api/games/1145350/reports/main").json()
        extension = client.post("/api/games/1145350/reports/main/extend")
        failed = wait_for_terminal_state(client, extension.json()["id"])
        report_after = client.get("/api/games/1145350/reports/main").json()

    assert failed["state"] == "failed"
    assert failed["error_code"] == "no_unseen_reviews"
    assert report_after["report_id"] == report_before["report_id"]


def wait_for_completion(client: TestClient, run_id: str) -> dict:
    response = client.get(f"/api/analysis-runs/{run_id}")
    for _ in range(100):
        if response.json()["state"] == "completed":
            break
        response = client.get(f"/api/analysis-runs/{run_id}")
    return response.json()


def wait_for_terminal_state(client: TestClient, run_id: str) -> dict:
    response = client.get(f"/api/analysis-runs/{run_id}")
    for _ in range(100):
        if response.json()["state"] in ("completed", "failed", "cancelled"):
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
