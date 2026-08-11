"""HTTP contract tests for durable Quick review imports."""

from collections.abc import Iterator
from pathlib import Path
from threading import Event
from time import monotonic, sleep

from fastapi.testclient import TestClient

from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.jobs import (
    checkpoint_page,
    create_job,
    start_job,
)
from game_review_analyzer.infrastructure.steam_reviews import (
    ReviewPage,
    SteamReviewsUnavailable,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings


class FailingOnceSource:
    """Fail the first import and exhaust Steam successfully on retry."""

    def __init__(self) -> None:
        self.calls: int = 0

    def iter_pages(self, _: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        self.calls += 1
        if self.calls == 1:
            raise SteamReviewsUnavailable("offline")
        yield ReviewPage(reviews=(), next_cursor=start_cursor)


class BlockingSource:
    """Hold the single worker so a second queued job can be cancelled deterministically."""

    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()

    def iter_pages(self, _: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        self.started.set()
        assert self.release.wait(timeout=2)
        yield ReviewPage(reviews=(), next_cursor=start_cursor)


class ResumeSource:
    """Record the durable cursor used after application restart."""

    def __init__(self) -> None:
        self.start_cursors: list[str] = []

    def iter_pages(self, _: int, start_cursor: str = "*") -> Iterator[ReviewPage]:
        self.start_cursors.append(start_cursor)
        yield ReviewPage(reviews=(), next_cursor=start_cursor)


def test_quick_import_exposes_failure_progress_retry_and_completion(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    settings = Settings(database_path=database_path)
    source = FailingOnceSource()

    with TestClient(create_app(settings, review_source=source)) as client:
        save_dataset(database_path)
        started = client.post("/api/games/1145350/imports/quick", json={"target_count": 5000})
        failed = wait_for_state(client, started.json()["id"], "failed")

        assert started.status_code == 202
        assert failed["error_code"] == "steam_unavailable"

        retried = client.post(f"/api/jobs/{failed['id']}/retry")
        completed = wait_for_state(client, failed["id"], "completed")

        assert retried.status_code == 202
        assert completed["target_count"] == 5000
        assert completed["imported_count"] == 0


def test_quick_import_validates_target_and_job_commands(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings, review_source=FailingOnceSource())) as client:
        invalid = client.post("/api/games/1145350/imports/quick", json={"target_count": 0})
        missing = client.get("/api/jobs/missing")
        cancel_missing = client.post("/api/jobs/missing/cancel")
        retry_missing = client.post("/api/jobs/missing/retry")

    assert invalid.status_code == 422
    assert missing.status_code == 404
    assert cancel_missing.status_code == 404
    assert retry_missing.status_code == 404


def test_quick_import_can_cancel_queued_work(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    source = BlockingSource()

    with TestClient(create_app(Settings(database_path=database_path), review_source=source)) as client:
        save_dataset(database_path)
        first = client.post("/api/games/1145350/imports/quick", json={"target_count": 1})
        assert source.started.wait(timeout=2)
        second = client.post("/api/games/1145350/imports/quick", json={"target_count": 1})

        cancelled = client.post(f"/api/jobs/{second.json()['id']}/cancel")
        source.release.set()

    assert first.status_code == 202
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"


def test_application_restart_resumes_an_interrupted_quick_import(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    initialize_database(database_path)
    save_dataset(database_path)
    job = create_job(database_path, app_id=1145350, target_count=2)
    assert start_job(database_path, job.id) is not None
    checkpoint_page(database_path, job.id, (steam_review(),), "resume-here")
    source = ResumeSource()

    with TestClient(create_app(Settings(database_path=database_path), review_source=source)) as client:
        completed = wait_for_state(client, job.id, "completed")

    assert completed["imported_count"] == 1
    assert source.start_cursors == ["resume-here"]


def wait_for_state(client: TestClient, job_id: str, state: str) -> dict[str, object]:
    deadline: float = monotonic() + 2
    while monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        if response.json()["state"] == state:
            return response.json()
        sleep(0.01)
    raise AssertionError(f"Job {job_id} did not reach {state}")


def save_dataset(database_path: Path) -> None:
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


def steam_review() -> SteamReview:
    return SteamReview(
        review_id="1001",
        language="english",
        text="Good game",
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
