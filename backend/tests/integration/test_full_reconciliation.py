"""Full acquisition and explicit non-destructive reconciliation tests."""

from collections.abc import Iterator
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.application.storage_lifecycle import verify_database_integrity
from game_review_analyzer.infrastructure.job_runner import JobRunner
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.jobs import (
    create_full_job,
    create_reconciliation_job,
    get_job,
    load_reconciliation_result,
    request_cancellation,
    retry_job,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
)
from game_review_analyzer.infrastructure.steam_reviews import (
    ReviewPage,
    SteamReviewsUnavailable,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from tests.integration.test_report_api import seed_report


class Pages:
    """Yield configured pages while recording the durable starting cursor."""

    def __init__(self, pages: tuple[ReviewPage, ...], expected_cursor: str = "*") -> None:
        self._pages = pages
        self._expected_cursor = expected_cursor

    def iter_pages(self, _: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        assert start_cursor == self._expected_cursor
        yield from self._pages


class InterruptedPages:
    """Yield one page and then simulate a bounded source failure."""

    def __init__(self, page: ReviewPage) -> None:
        self._page = page

    def iter_pages(self, _: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        assert start_cursor == "*"
        yield self._page
        raise SteamReviewsUnavailable("offline")


def test_full_import_resumes_large_bounded_pagination_and_can_cancel(
    tmp_path: Path,
) -> None:
    database_path: Path = initialized_dataset(tmp_path, review_count=250)
    reviews: tuple[SteamReview, ...] = tuple(review(index) for index in range(250))
    job = create_full_job(database_path, 1145350)
    first = ReviewPage(reviews=reviews[:100], next_cursor="page-2")

    JobRunner(database_path, InterruptedPages(first)).run(job.id)
    assert get_job(database_path, job.id).state == "failed"
    assert get_job(database_path, job.id).imported_count == 100
    assert verify_database_integrity(database_path).orphan_count == 0

    retry_job(database_path, job.id)
    JobRunner(
        database_path,
        Pages(
            (
                ReviewPage(reviews=reviews[100:200], next_cursor="page-3"),
                ReviewPage(reviews=reviews[200:], next_cursor="done"),
            ),
            expected_cursor="page-2",
        ),
    ).run(job.id)

    completed = get_job(database_path, job.id)
    assert completed.state == "completed"
    assert completed.scope == "full"
    assert completed.imported_count == 250
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM job_checkpoints").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM review_revisions").fetchone()[0] == 250
    assert verify_database_integrity(database_path).sqlite_ok is True

    cancelled = create_full_job(database_path, 1145350)
    request_cancellation(database_path, cancelled.id)
    assert get_job(database_path, cancelled.id).state == "cancelled"


def test_reconciliation_records_missing_reviews_without_mutating_evidence(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)
    with sqlite3.connect(database_path) as connection:
        before_revisions: list[tuple[int, str]] = connection.execute(
            "SELECT id, content_json FROM review_revisions ORDER BY id"
        ).fetchall()
        before_report: str = connection.execute(
            "SELECT snapshot_json FROM report_versions WHERE id = 'report-1'"
        ).fetchone()[0]
    present_review: SteamReview = load_review_revisions_by_ids(
        database_path, (before_revisions[0][0],)
    )[before_revisions[0][0]]
    job = create_reconciliation_job(database_path, 1145350)
    source = Pages(
        (
            ReviewPage(
                reviews=(present_review,),
                next_cursor="done",
            ),
            ReviewPage(reviews=(), next_cursor="done"),
        )
    )

    JobRunner(database_path, source).run(job.id)

    result = load_reconciliation_result(database_path, job.id)
    assert result.missing_review_ids == ("review-2",)
    assert result.present_review_count == 1
    with sqlite3.connect(database_path) as connection:
        after_revisions: list[tuple[int, str]] = connection.execute(
            "SELECT id, content_json FROM review_revisions ORDER BY id"
        ).fetchall()
        after_report: str = connection.execute(
            "SELECT snapshot_json FROM report_versions WHERE id = 'report-1'"
        ).fetchone()[0]
    assert after_revisions == before_revisions
    assert after_report == before_report


def test_full_and_reconciliation_http_contract(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)
    source = Pages((ReviewPage(reviews=(), next_cursor="done"),))

    with TestClient(
        create_app(Settings(database_path=database_path), review_source=source)
    ) as client:
        full_response = client.post("/api/games/1145350/imports/full")
        reconciliation_response = client.post(
            "/api/games/1145350/reconciliations"
        )

    assert full_response.status_code == 202
    assert full_response.json()["scope"] == "full"
    assert reconciliation_response.status_code == 202
    assert reconciliation_response.json()["scope"] == "reconciliation"


def initialized_dataset(tmp_path: Path, review_count: int) -> Path:
    """Create one empty dataset with a known Full-import upper bound."""

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
    return database_path


def review(
    index: int,
    *,
    review_id: str | None = None,
    text: str | None = None,
) -> SteamReview:
    """Build one normalized Full-import fixture review."""

    return SteamReview(
        review_id=review_id or f"review-{index}",
        language="english",
        text=text or f"Review {index}",
        source_created_at=100,
        source_updated_at=100,
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
