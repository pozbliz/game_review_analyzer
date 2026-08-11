"""Append-only persistence tests for Steam Review Revisions."""

from pathlib import Path
import sqlite3

from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.review_revisions import save_review_revisions


def review(text: str, updated_at: int) -> SteamReview:
    return SteamReview(
        review_id="1001",
        language="english",
        text=text,
        source_created_at=100,
        source_updated_at=updated_at,
        recommended=True,
        votes_helpful=12,
        votes_funny=1,
        weighted_vote_score=0.8,
        steam_purchase=True,
        received_for_free=False,
        written_during_early_access=True,
        playtime_forever_minutes=3000,
        playtime_at_review_minutes=2400,
    )


def test_duplicate_reviews_do_not_create_duplicate_revisions(tmp_path: Path) -> None:
    database_path = initialized_dataset(tmp_path)
    original = review("Combat feels responsive.", 100)

    assert save_review_revisions(database_path, 1145350, (original, original)) == 1
    assert save_review_revisions(database_path, 1145350, (original,)) == 0

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM review_revisions").fetchone()[0] == 1


def test_edited_review_appends_revision_without_changing_original(tmp_path: Path) -> None:
    database_path = initialized_dataset(tmp_path)
    original = review("Combat feels responsive.", 100)
    edited = review("Combat feels exceptionally responsive.", 120)

    save_review_revisions(database_path, 1145350, (original,))
    assert save_review_revisions(database_path, 1145350, (edited,)) == 1

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT source_updated_at, content_json FROM review_revisions ORDER BY id"
        ).fetchall()
    assert [row[0] for row in rows] == [100, 120]
    assert "Combat feels responsive." in rows[0][1]
    assert "Combat feels exceptionally responsive." in rows[1][1]


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
