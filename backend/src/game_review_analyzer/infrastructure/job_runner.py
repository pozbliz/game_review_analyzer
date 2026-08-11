"""Durable Quick review import state machine."""

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from game_review_analyzer.infrastructure.persistence.jobs import (
    cancellation_requested,
    checkpoint_page,
    finish_job,
    start_job,
)
from game_review_analyzer.infrastructure.steam_reviews import (
    ReviewCursorRepeated,
    ReviewPage,
    SteamReviewsMalformed,
    SteamReviewsUnavailable,
)


class ReviewPageSource(Protocol):
    """Allow the runner to consume any checkpoint-sized normalized review source."""

    def iter_pages(self, app_id: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        """Yield normalized pages beginning at a durable cursor."""


class JobRunner:
    """Run one durable Quick import synchronously for a background worker."""

    def __init__(self, database_path: Path, source: ReviewPageSource) -> None:
        self._database_path = database_path
        self._source = source

    def run(self, job_id: str) -> None:
        """Advance a queued job until completion, cancellation, or bounded failure."""

        job = start_job(self._database_path, job_id)
        if job is None:
            return
        try:
            for page in self._source.iter_pages(job.app_id, job.cursor):
                if cancellation_requested(self._database_path, job_id):
                    finish_job(self._database_path, job_id, "cancelled")
                    return
                if not page.reviews:
                    finish_job(self._database_path, job_id, "completed")
                    return
                remaining: int = job.target_count - job.imported_count
                selected_reviews = page.reviews[:remaining]
                job = checkpoint_page(
                    self._database_path,
                    job_id,
                    selected_reviews,
                    page.next_cursor,
                )
                if job.imported_count >= job.target_count:
                    finish_job(self._database_path, job_id, "completed")
                    return
            finish_job(self._database_path, job_id, "completed")
        except SteamReviewsUnavailable:
            finish_job(self._database_path, job_id, "failed", "steam_unavailable")
        except SteamReviewsMalformed:
            finish_job(self._database_path, job_id, "failed", "invalid_steam_response")
        except ReviewCursorRepeated:
            finish_job(self._database_path, job_id, "failed", "cursor_repeated")
