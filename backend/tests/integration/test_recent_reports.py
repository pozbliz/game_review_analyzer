"""Recent current-report navigation through the public API."""

from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.persistence.report_versions import (
    load_aggregate_report_slot,
    save_aggregate_report,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import save_review_revisions
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from tests.integration.aggregate_report_seed import review, seed_aggregate_report


def test_recent_reports_list_current_slots_newest_first(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    with TestClient(create_app(Settings(database_path=database_path))) as client:
        empty_response = client.get("/api/reports/recent")
        assert empty_response.status_code == 200
        assert empty_response.json() == []

        seed_aggregate_report(database_path)
        main_report = load_aggregate_report_slot(database_path, 1145350, "main")
        assert main_report is not None
        save_aggregate_report(
            database_path,
            main_report.model_copy(update={"report_id": "test-1", "kind": "test"}),
        )
        metadata = main_report.metadata_snapshot.model_copy(
            update={"app_id": 413150, "title": "Stardew Valley"}
        )
        save_game_dataset(database_path, metadata)
        save_review_revisions(database_path, 413150, (
            review("stardew-1", "Combat is responsive.", True, 3),
            review("stardew-2", "Fights feel responsive.", False, 20),
        ))
        with sqlite3.connect(database_path) as connection:
            revision_ids: tuple[int, ...] = tuple(
                row[0] for row in connection.execute(
                    "SELECT review_revisions.id FROM review_revisions "
                    "JOIN reviews ON reviews.id = review_revisions.review_id "
                    "WHERE reviews.app_id = 413150 ORDER BY review_revisions.id"
                )
            )
        save_aggregate_report(database_path, main_report.model_copy(update={
            "report_id": "stardew-main", "app_id": 413150,
            "metadata_snapshot": metadata, "review_revision_ids": revision_ids,
            "oldest_review_revision_ids": revision_ids[:1],
            "newest_review_revision_ids": revision_ids[1:],
            "memberships": tuple(
                membership.model_copy(update={"review_revision_id": revision_id})
                for membership, revision_id in zip(main_report.memberships, revision_ids)
            ),
        }))
        with sqlite3.connect(database_path) as connection:
            connection.executemany(
                "UPDATE report_versions SET created_at = ? WHERE id = ?",
                (("2026-10-01 12:00:00", "report-1"),
                 ("2026-10-03 10:00:00", "test-1"),
                 ("2026-10-02 12:00:00", "stardew-main")),
            )
        response = client.get("/api/reports/recent")

        assert response.status_code == 200
        assert response.json() == [
            {"report_id": "test-1", "app_id": 1145350, "title": "Hades II",
             "kind": "test", "review_count": 2, "created_at": "2026-10-03 10:00:00"},
            {"report_id": "stardew-main", "app_id": 413150, "title": "Stardew Valley",
             "kind": "main", "review_count": 2, "created_at": "2026-10-02 12:00:00"},
            {"report_id": "report-1", "app_id": 1145350, "title": "Hades II",
             "kind": "main", "review_count": 2, "created_at": "2026-10-01 12:00:00"},
        ]

        save_aggregate_report(
            database_path,
            main_report.model_copy(update={"report_id": "main-replacement"}),
        )
        updated_ids: list[str] = [
            item["report_id"] for item in client.get("/api/reports/recent").json()
        ]
        assert updated_ids[0] == "main-replacement"
        assert "report-1" not in updated_ids
        assert len(updated_ids) == 3
