"""Durable per-review cache for validated Opinion Point extraction."""

from collections.abc import Iterable
import json
from pathlib import Path

from game_review_analyzer.domain.analysis import (
    ExtractedOpinionPoint,
    OpinionExtractionResult,
)
from game_review_analyzer.infrastructure.persistence.jobs import connect


def save_opinion_extraction_batch(
    database_path: Path,
    *,
    revision_ids_by_review_id: dict[str, int],
    result: OpinionExtractionResult,
    contract_version: str,
) -> None:
    """Cache one validated batch atomically, including reviews with no opinions."""

    completed_ids: set[str] = set(result.completed_review_revision_ids)
    if completed_ids != set(revision_ids_by_review_id):
        raise ValueError("Extraction cache scope does not match the completed batch")
    points_by_review_id: dict[str, list[ExtractedOpinionPoint]] = {
        review_id: [] for review_id in completed_ids
    }
    for point in result.opinion_points:
        if point.review_revision_id not in points_by_review_id:
            raise ValueError("Extraction references a review outside the batch")
        points_by_review_id[point.review_revision_id].append(point)

    with connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        for review_id, revision_id in revision_ids_by_review_id.items():
            normalized_points: tuple[ExtractedOpinionPoint, ...] = tuple(
                point.model_copy(
                    update={
                        "id": f"revision-{revision_id}-opinion-{position}",
                    }
                )
                for position, point in enumerate(
                    points_by_review_id[review_id], start=1
                )
            )
            connection.execute(
                "INSERT INTO review_opinion_extractions("
                "review_revision_id, provider, model, contract_version, "
                "opinion_points_json) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT DO NOTHING",
                (
                    revision_id,
                    result.provider,
                    result.model,
                    contract_version,
                    json.dumps(
                        [point.model_dump(mode="json") for point in normalized_points],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                ),
            )


def load_opinion_extractions(
    database_path: Path,
    *,
    revision_ids: Iterable[int],
    provider: str,
    model: str,
    contract_version: str,
) -> dict[int, tuple[ExtractedOpinionPoint, ...]]:
    """Return cached extractions for the requested exact provider contract."""

    identifiers: tuple[int, ...] = tuple(revision_ids)
    if not identifiers:
        return {}
    placeholders: str = ",".join("?" for _ in identifiers)
    with connect(database_path) as connection:
        rows: list[tuple[int, str]] = connection.execute(
            "SELECT review_revision_id, opinion_points_json "
            "FROM review_opinion_extractions "
            f"WHERE review_revision_id IN ({placeholders}) "
            "AND provider = ? AND model = ? AND contract_version = ?",
            (*identifiers, provider, model, contract_version),
        ).fetchall()
    return {
        int(revision_id): tuple(
            ExtractedOpinionPoint.model_validate(point)
            for point in json.loads(points_json)
        )
        for revision_id, points_json in rows
    }
