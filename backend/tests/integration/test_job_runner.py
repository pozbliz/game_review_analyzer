"""Durable state-transition tests for Quick review import jobs."""

from collections.abc import Iterator
from pathlib import Path
import sqlite3

from game_review_analyzer.infrastructure.job_runner import JobRunner
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.jobs import (
    create_job,
    get_job,
    recoverable_job_ids,
    request_cancellation,
    retry_job,
)
from game_review_analyzer.infrastructure.steam_reviews import (
    ReviewPage,
    SteamReviewsUnavailable,
)


class PageSource:
    """Yield configured pages through the runner's ingestion seam."""

    def __init__(self, pages: tuple[ReviewPage, ...]) -> None:
        self.pages = pages

    def iter_pages(self, _: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        assert start_cursor
        yield from self.pages


class FailingSource:
    """Raise one configured source failure when a job begins."""

    def iter_pages(self, _: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        raise SteamReviewsUnavailable("offline")
        yield ReviewPage(reviews=(), next_cursor=start_cursor)


def steam_review(review_id: str) -> SteamReview:
    return SteamReview(
        review_id=review_id,
        language="english",
        text=f"Review {review_id}",
        source_created_at=100,
        source_updated_at=100,
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


def test_runner_completes_at_target_with_atomic_checkpoint(tmp_path: Path) -> None:
    database_path = initialized_dataset(tmp_path)
    job = create_job(database_path, app_id=1145350, target_count=2)
    source = PageSource(
        (
            ReviewPage(
                reviews=(steam_review("1001"), steam_review("1002"), steam_review("1003")),
                next_cursor="next",
            ),
        )
    )

    JobRunner(database_path, source).run(job.id)

    completed = get_job(database_path, job.id)
    assert completed.state == "completed"
    assert completed.imported_count == 2
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM job_checkpoints").fetchone()[0] == 1


def test_queued_job_can_be_cancelled_without_running(tmp_path: Path) -> None:
    database_path = initialized_dataset(tmp_path)
    job = create_job(database_path, app_id=1145350, target_count=100)

    request_cancellation(database_path, job.id)

    assert get_job(database_path, job.id).state == "cancelled"


def test_failed_job_retries_from_its_durable_state(tmp_path: Path) -> None:
    database_path = initialized_dataset(tmp_path)
    job = create_job(database_path, app_id=1145350, target_count=100)

    JobRunner(database_path, FailingSource()).run(job.id)
    failed = get_job(database_path, job.id)
    assert failed.state == "failed"
    assert failed.error_code == "steam_unavailable"

    retry_job(database_path, job.id)
    JobRunner(
        database_path,
        PageSource((ReviewPage(reviews=(), next_cursor="done"),)),
    ).run(job.id)

    assert get_job(database_path, job.id).state == "completed"


def test_restart_requeues_abandoned_running_jobs(tmp_path: Path) -> None:
    database_path = initialized_dataset(tmp_path)
    job = create_job(database_path, app_id=1145350, target_count=100)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE analysis_jobs SET state = 'running' WHERE id = ?",
            (job.id,),
        )

    assert recoverable_job_ids(database_path) == [job.id]
    assert get_job(database_path, job.id).state == "queued"


def initialized_dataset(tmp_path: Path) -> Path:
    database_path = tmp_path / "app.sqlite3"
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
            review_count=None,
            source_status="partial",
            missing_fields=frozenset(
                {"capsule_image_url", "release_date", "release_status", "review_count"}
            ),
        ),
    )
    return database_path
