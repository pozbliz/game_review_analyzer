"""Append-only refresh integration tests."""

from collections.abc import Iterator
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.infrastructure.job_runner import JobRunner
from game_review_analyzer.infrastructure.persistence.jobs import (
    create_refresh_job,
    get_job,
    load_job_analysis_scope,
    retry_job,
)
from game_review_analyzer.infrastructure.steam_reviews import (
    ReviewPage,
    SteamReviewsUnavailable,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from tests.integration.aggregate_report_seed import seed_aggregate_report


class RefreshPageSource:
    """Yield deterministic refresh pages through the production runner seam."""

    def __init__(self, pages: tuple[ReviewPage, ...]) -> None:
        self._pages = pages

    def iter_pages(self, _: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        assert start_cursor
        yield from self._pages


class InterruptedRefreshSource:
    """Checkpoint one page, then simulate a retryable Steam interruption."""

    def __init__(self, page: ReviewPage) -> None:
        self._page = page

    def iter_pages(self, _: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        assert start_cursor == "*"
        yield self._page
        raise SteamReviewsUnavailable("offline")


def test_refresh_appends_only_new_and_edited_revisions_and_checkpoints_scope(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_aggregate_report(database_path)
    before: tuple[str, list[tuple[int, str]], str] = stored_history(database_path)
    job = create_refresh_job(database_path, app_id=1145350, target_count=3)
    page = ReviewPage(
        reviews=(
            review("review-1", "Combat is responsive.", 100, True, 120, 3),
            review("review-2", "Fights feel much smoother now.", 200, False, 300, 6),
            review("review-3", "New weapons are excellent.", 200, True, 60, 1),
        ),
        next_cursor="next",
    )

    JobRunner(database_path, RefreshPageSource((page,))).run(job.id)

    assert get_job(database_path, job.id).state == "completed"
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM review_revisions").fetchone()[0] == 4
        latest_ids: tuple[int, ...] = tuple(
            row[0]
            for row in connection.execute(
                "SELECT MAX(review_revisions.id) FROM review_revisions "
                "JOIN reviews ON reviews.id = review_revisions.review_id "
                "WHERE reviews.app_id = 1145350 GROUP BY reviews.id ORDER BY MAX(review_revisions.id)"
            )
        )
    assert load_job_analysis_scope(database_path, job.id) == latest_ids
    assert stored_history(database_path) == before


def test_refresh_retry_resumes_from_page_checkpoint_before_reanalysis(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_aggregate_report(database_path)
    job = create_refresh_job(database_path, app_id=1145350, target_count=2)
    first_page = ReviewPage(
        reviews=(review("review-1", "Combat is responsive.", 100, True, 120, 3),),
        next_cursor="after-first",
    )
    JobRunner(database_path, InterruptedRefreshSource(first_page)).run(job.id)

    assert get_job(database_path, job.id).state == "failed"
    assert get_job(database_path, job.id).cursor == "after-first"
    assert load_job_analysis_scope(database_path, job.id) is None

    retry_job(database_path, job.id)
    second_page = ReviewPage(
        reviews=(review("review-3", "New weapons are excellent.", 200, True, 60, 1),),
        next_cursor="done",
    )
    JobRunner(database_path, RefreshPageSource((second_page,))).run(job.id)

    assert get_job(database_path, job.id).state == "completed"
    assert load_job_analysis_scope(database_path, job.id) is not None


def test_refresh_http_contract_does_not_restore_report_history(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_aggregate_report(database_path)
    source = RefreshPageSource((ReviewPage(reviews=(), next_cursor="done"),))

    with TestClient(
        create_app(Settings(database_path=database_path), review_source=source)
    ) as client:
        refresh_response = client.post(
            "/api/games/1145350/refreshes", json={"target_count": 5000}
        )
        history_response = client.get("/api/games/1145350/reports")
        recent_response = client.get("/api/reports/recent")

    assert refresh_response.status_code == 202
    assert refresh_response.json()["scope"] == "refresh"
    assert history_response.status_code == 404
    assert recent_response.status_code == 404


def stored_history(database_path: Path) -> tuple[str, list[tuple[int, str]], str]:
    """Capture immutable report, revision, and current metadata bytes."""

    with sqlite3.connect(database_path) as connection:
        report_json: str = connection.execute(
            "SELECT snapshot_json FROM report_versions WHERE id = 'report-1'"
        ).fetchone()[0]
        revisions: list[tuple[int, str]] = connection.execute(
            "SELECT id, content_json FROM review_revisions ORDER BY id LIMIT 2"
        ).fetchall()
        metadata_json: str = connection.execute(
            "SELECT metadata_json FROM game_datasets WHERE app_id = 1145350"
        ).fetchone()[0]
    return report_json, revisions, metadata_json


def review(
    review_id: str,
    text: str,
    updated_at: int,
    recommended: bool,
    playtime_at_review: int,
    helpful: int,
) -> SteamReview:
    """Build one normalized refresh fixture review."""

    return SteamReview(
        review_id=review_id,
        language="english",
        text=text,
        source_created_at=100,
        source_updated_at=updated_at,
        recommended=recommended,
        votes_helpful=helpful,
        votes_funny=0,
        weighted_vote_score=0,
        steam_purchase=True,
        received_for_free=False,
        written_during_early_access=False,
        playtime_forever_minutes=playtime_at_review + 60,
        playtime_at_review_minutes=playtime_at_review,
    )
