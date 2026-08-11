"""Safe report export and JSON re-import integration tests."""

import csv
from io import StringIO
import json
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from game_review_analyzer.application.report_exports import (
    export_report_csv,
    export_report_html,
    export_report_json,
    import_report_json,
)
from game_review_analyzer.domain.analysis import AnalysisResult, OpinionPoint, Theme
from game_review_analyzer.domain.reports import ReportVersion
from game_review_analyzer.infrastructure.persistence.game_datasets import (
    load_game_dataset,
    save_game_dataset,
)
from game_review_analyzer.infrastructure.persistence.report_versions import (
    load_report_version,
    save_report_version,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from tests.integration.test_report_api import seed_report


def test_json_contract_round_trips_only_with_exact_local_evidence(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)

    exported: str = export_report_json(database_path, "report-1")
    document: dict[str, object] = json.loads(exported)

    assert document["kind"] == "game-review-analyzer-report"
    assert document["format_version"] == "1.0"
    assert document["full_review_text_included"] is False
    assert "Combat is responsive." not in exported
    assert all("review_text" not in item for item in document["evidence_bindings"])
    assert len(document["evidence_bindings"]) == 2

    delete_report(database_path)
    imported: ReportVersion = import_report_json(database_path, exported)
    assert imported.report_version_id == "report-1"
    assert load_report_version(database_path, "report-1") == imported


def test_json_import_rejects_missing_mismatched_and_undeclared_evidence(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)
    exported: str = export_report_json(database_path, "report-1")
    delete_report(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM review_revisions WHERE id = 2")

    with pytest.raises(ValueError, match="missing or mismatched"):
        import_report_json(database_path, exported)

    mismatched_path: Path = tmp_path / "mismatched.sqlite3"
    seed_report(mismatched_path)
    delete_report(mismatched_path)
    with sqlite3.connect(mismatched_path) as connection:
        connection.execute(
            "UPDATE review_revisions SET content_hash = ? WHERE id = 2",
            ("b" * 64,),
        )
    with pytest.raises(ValueError, match="missing or mismatched"):
        import_report_json(mismatched_path, exported)

    for undeclared_field in ("api_key", "reviewer_steam_id"):
        document: dict[str, object] = json.loads(exported)
        document[undeclared_field] = "must-not-be-accepted"
        with pytest.raises(ValueError, match="Invalid report export"):
            import_report_json(database_path, json.dumps(document))


def test_csv_preserves_theme_evidence_relationships_and_quotes_formulas(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)
    unsafe_report(database_path)

    default_rows: list[dict[str, str]] = list(
        csv.DictReader(StringIO(export_report_csv(database_path, "unsafe-report")))
    )
    full_rows: list[dict[str, str]] = list(
        csv.DictReader(
            StringIO(
                export_report_csv(
                    database_path,
                    "unsafe-report",
                    include_full_review_text=True,
                )
            )
        )
    )

    assert default_rows[0]["theme_id"] == "responsive-combat"
    assert default_rows[0]["opinion_point_id"] == "point-1"
    assert default_rows[0]["source_review_id"] == "review-1"
    assert default_rows[0]["theme_title"].startswith("'")
    assert default_rows[0]["review_text"] == ""
    assert full_rows[0]["review_text"] == "Combat is responsive."
    assert "privacy" in full_rows[0]["privacy_warning"].lower()


def test_html_escapes_untrusted_content_and_blocks_unsafe_media(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)
    unsafe_report(database_path)
    metadata = load_game_dataset(database_path, 1145350)
    assert metadata is not None
    save_game_dataset(
        database_path,
        metadata.model_copy(
            update={
                "capsule_image_url": "javascript:alert(1)",
                "missing_fields": metadata.missing_fields - {"capsule_image_url"},
            }
        ),
    )

    exported: str = export_report_html(database_path, "unsafe-report")

    assert exported.startswith("<!doctype html>")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in exported
    assert "<script>" not in exported
    assert "javascript:" not in exported
    assert "Combat is responsive." not in exported
    assert "External Steam-hosted media is not embedded" in exported
    assert "reviewer_name" not in exported.lower()
    assert "steamid" not in exported.lower()


def test_json_full_text_requires_an_explicit_option_and_carries_a_warning(
    tmp_path: Path,
) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)

    exported: dict[str, object] = json.loads(
        export_report_json(
            database_path,
            "report-1",
            include_full_review_text=True,
        )
    )

    assert exported["full_review_text_included"] is True
    assert "privacy" in str(exported["privacy_warning"]).lower()
    assert exported["evidence_bindings"][0]["review_text"] == "Combat is responsive."


def test_export_download_and_json_import_http_contract(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "app.sqlite3"
    seed_report(database_path)

    with TestClient(create_app(Settings(database_path=database_path))) as client:
        json_response = client.get("/api/reports/report-1/export?format=json")
        csv_response = client.get("/api/reports/report-1/export?format=csv")
        html_response = client.get("/api/reports/report-1/export?format=html")
        exported: str = json_response.text
        delete_report(database_path)
        import_response = client.post(
            "/api/reports/import",
            content=exported,
            headers={"content-type": "application/json"},
        )

    assert json_response.status_code == 200
    assert json_response.headers["content-type"].startswith("application/json")
    assert "attachment" in json_response.headers["content-disposition"]
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert html_response.headers["content-type"].startswith("text/html")
    assert import_response.status_code == 201
    assert import_response.json()["report_version_id"] == "report-1"


def delete_report(database_path: Path) -> None:
    """Delete only the exported report while retaining its local evidence."""

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("DELETE FROM report_versions WHERE id = 'report-1'")


def unsafe_report(database_path: Path) -> None:
    """Add a report containing markup and spreadsheet-formula payloads."""

    source: ReportVersion | None = load_report_version(database_path, "report-1")
    assert source is not None
    source_theme: Theme = source.analysis_result.themes[0]
    unsafe_theme: Theme = source_theme.model_copy(
        update={
            "title": '\t=HYPERLINK("https://example.test")',
            "summary": "<script>alert(1)</script>",
        }
    )
    points: tuple[OpinionPoint, ...] = source.analysis_result.opinion_points
    analysis: AnalysisResult = source.analysis_result.model_copy(
        update={"themes": (unsafe_theme,), "opinion_points": points}
    )
    save_report_version(
        database_path,
        source.model_copy(
            update={"report_version_id": "unsafe-report", "analysis_result": analysis}
        ),
    )
