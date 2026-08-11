"""Append-only SQLite persistence for normalized Steam reviews."""

from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path
import sqlite3

from game_review_analyzer.domain.reviews import SteamReview


def save_review_revisions(
    database_path: Path,
    app_id: int,
    reviews: Iterable[SteamReview],
) -> int:
    """Persist reviews and return the number of newly appended revisions."""

    inserted_revisions: int = 0
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for review in reviews:
            connection.execute(
                "INSERT INTO reviews(id, app_id) VALUES (?, ?) "
                "ON CONFLICT(id) DO NOTHING",
                (review.review_id, app_id),
            )
            content_json: str = review.model_dump_json()
            content_hash: str = sha256(content_json.encode("utf-8")).hexdigest()
            cursor: sqlite3.Cursor = connection.execute(
                "INSERT INTO review_revisions("
                "review_id, source_updated_at, content_hash, content_json) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(review_id, source_updated_at, content_hash) DO NOTHING",
                (
                    review.review_id,
                    review.source_updated_at,
                    content_hash,
                    content_json,
                ),
            )
            inserted_revisions += cursor.rowcount
    return inserted_revisions
