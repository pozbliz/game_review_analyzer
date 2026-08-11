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
        inserted_revisions = insert_review_revisions(connection, app_id, reviews)
    return inserted_revisions


def insert_review_revisions(
    connection: sqlite3.Connection,
    app_id: int,
    reviews: Iterable[SteamReview],
) -> int:
    """Append revisions inside a caller-owned SQLite transaction."""

    inserted_revisions: int = 0
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


def load_review_revisions_by_ids(
    database_path: Path,
    revision_ids: Iterable[int],
) -> dict[int, SteamReview]:
    """Load exact immutable Review Revisions by their local identifiers."""

    identifiers: tuple[int, ...] = tuple(revision_ids)
    if not identifiers:
        return {}
    placeholders: str = ",".join("?" for _ in identifiers)
    with sqlite3.connect(database_path) as connection:
        rows: list[tuple[int, str]] = connection.execute(
            f"SELECT id, content_json FROM review_revisions WHERE id IN ({placeholders})",
            identifiers,
        ).fetchall()
    revisions: dict[int, SteamReview] = {
        row[0]: SteamReview.model_validate_json(row[1]) for row in rows
    }
    if set(revisions) != set(identifiers):
        raise ValueError("One or more Review Revisions are unavailable")
    return revisions


def match_review_revision_ids(
    database_path: Path,
    app_id: int,
    content_sha256_by_review_id: dict[str, str],
) -> dict[str, int]:
    """Resolve exact local revisions for a versioned report import."""

    review_ids: tuple[str, ...] = tuple(content_sha256_by_review_id)
    if not review_ids:
        return {}
    placeholders: str = ",".join("?" for _ in review_ids)
    with sqlite3.connect(database_path) as connection:
        rows: list[tuple[int, str, str]] = connection.execute(
            "SELECT review_revisions.id, reviews.id, review_revisions.content_hash "
            "FROM review_revisions JOIN reviews ON reviews.id = review_revisions.review_id "
            f"WHERE reviews.app_id = ? AND reviews.id IN ({placeholders})",
            (app_id, *review_ids),
        ).fetchall()
    matches: dict[str, int] = {
        review_id: revision_id
        for revision_id, review_id, content_sha256 in rows
        if content_sha256_by_review_id.get(review_id) == content_sha256
    }
    if set(matches) != set(content_sha256_by_review_id):
        raise ValueError("Report evidence is missing or mismatched")
    return matches
