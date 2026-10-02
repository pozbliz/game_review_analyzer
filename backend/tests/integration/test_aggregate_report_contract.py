"""Public Version 3 report route contract tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings


def test_only_current_main_and_test_report_routes_are_exposed(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(database_path=tmp_path / "app.sqlite3"))) as client:
        report_paths: set[str] = {
            path for path in client.app.openapi()["paths"] if "report" in path
        }

    assert report_paths == {
        "/api/games/{app_id}/reports/test",
        "/api/games/{app_id}/reports/main",
        "/api/games/{app_id}/reports/main/extend",
        "/api/reports/{report_version_id}/delete",
    }
    assert "/api/providers/ollama" not in client.app.openapi()["paths"]
    assert "/api/games/{app_id}/analyses/ollama" not in client.app.openapi()["paths"]
    assert "/api/games/{app_id}/analyses/codex-cli" not in client.app.openapi()["paths"]
