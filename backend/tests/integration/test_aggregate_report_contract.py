"""Public Version 3 report route contract tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from tests.integration.aggregate_report_seed import seed_aggregate_report


def test_only_current_main_and_test_report_routes_are_exposed(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(database_path=tmp_path / "app.sqlite3"))) as client:
        report_paths: set[str] = {
            path for path in client.app.openapi()["paths"] if "report" in path
        }

    assert report_paths == {
        "/api/games/{app_id}/reports/test",
        "/api/games/{app_id}/reports/main",
        "/api/games/{app_id}/reports/main/extend",
        "/api/games/{app_id}/reports/{kind}/themes/{theme_id}/evidence",
        "/api/reports/{report_version_id}/delete",
    }
    assert "/api/providers/ollama" not in client.app.openapi()["paths"]
    assert "/api/games/{app_id}/analyses/ollama" not in client.app.openapi()["paths"]
    assert "/api/games/{app_id}/analyses/codex-cli" not in client.app.openapi()["paths"]


def test_report_theme_evidence_uses_memberships_and_orders_helpful_first(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_aggregate_report(database_path)

    with TestClient(create_app(Settings(database_path=database_path))) as client:
        response = client.get(
            "/api/games/1145350/reports/main/themes/responsive-combat/evidence"
        )
        missing_theme = client.get(
            "/api/games/1145350/reports/main/themes/unknown/evidence"
        )

    assert response.status_code == 200
    assert response.json() == {
        "theme_id": "responsive-combat",
        "title": "Responsive combat",
        "reviews": [
            {
                "review_revision_id": 2,
                "text": "Fights feel responsive.",
                "recommended": False,
                "votes_helpful": 20,
            },
            {
                "review_revision_id": 1,
                "text": "Combat is responsive.",
                "recommended": True,
                "votes_helpful": 3,
            },
        ],
    }
    assert missing_theme.status_code == 404
    assert missing_theme.json()["detail"]["code"] == "theme_not_found"
