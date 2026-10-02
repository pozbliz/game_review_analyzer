"""Behavior tests for the local application shell."""

from pathlib import Path

from fastapi.testclient import TestClient

from game_review_analyzer.infrastructure.persistence.database import (
    CURRENT_SCHEMA_VERSION,
    schema_version,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.infrastructure.codex_cli import CodexCliStatus
from game_review_analyzer.shared.config import Settings
from game_review_analyzer.shared.telemetry import read_events


def test_health_endpoint_reports_ready_service(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "game-review-analyzer"}


def test_diagnostics_endpoint_exposes_redacted_application_errors(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings)) as client:
        missing = client.get("/api/missing")
    events = read_events(settings.database_path.with_suffix(".log"))

    assert missing.status_code == 404
    event = events[-1]
    assert event["event"] == "http.response_error"
    assert event["path"] == "/api/missing"
    assert event["status_code"] == 404
    assert "query" not in event


def test_browser_diagnostics_accept_only_redacted_failure_context(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings)) as client:
        recorded = client.post("/api/diagnostics/client", json={
            "event": "frontend.error",
            "path": "/reports/report-1",
            "error_type": "TypeError",
        })
    events = read_events(settings.database_path.with_suffix(".log"))

    assert recorded.status_code == 204
    assert events[-1] == {
        "timestamp": events[-1]["timestamp"],
        "level": "error",
        "event": "frontend.error",
        "path": "/reports/report-1",
        "error_type": "TypeError",
    }


def test_application_lifespan_applies_sqlite_migrations(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "app.sqlite3"
    settings = Settings(database_path=database_path)

    with TestClient(create_app(settings)):
        pass

    assert schema_version(database_path) == CURRENT_SCHEMA_VERSION


def test_public_config_does_not_expose_database_path(tmp_path: Path) -> None:
    settings = Settings(environment="test", database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/config")

    assert response.json() == {
        "environment": "test",
        "api_prefix": "/api",
        "steam_country_code": "US",
        "keyed_catalog_available": False,
    }
    assert "database_path" not in response.text


def test_codex_provider_status_discloses_cloud_and_quota_without_credentials(
    tmp_path: Path,
) -> None:
    settings = Settings(environment="test", database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(
        settings,
        codex_status_source=lambda: CodexCliStatus(
            installed=True,
            authenticated=True,
            version="codex-cli 0.147.0",
            model="gpt-5.6-luna",
            reasoning_effort="medium",
        ),
    )) as client:
        response = client.get("/api/providers/codex-cli")

    assert response.status_code == 200
    assert response.json() == {
        "installed": True,
        "authenticated": True,
        "version": "codex-cli 0.147.0",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "medium",
        "processing_location": "external_cloud",
        "cost_basis": "subscription_quota_unknown",
    }
    assert "credential" not in response.text.lower()


def test_shell_endpoints_publish_explicit_response_contracts(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings)) as client:
        schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert schemas["HealthResponse"]["required"] == ["status", "service"]
    assert schemas["PublicConfigResponse"]["required"] == [
        "environment",
        "api_prefix",
        "steam_country_code",
        "keyed_catalog_available",
    ]


def test_compiled_frontend_is_served_without_shadowing_api_routes(tmp_path: Path) -> None:
    frontend_path = tmp_path / "dist"
    assets_path = frontend_path / "assets"
    assets_path.mkdir(parents=True)
    (frontend_path / "index.html").write_text("<h1>Compiled frontend</h1>", encoding="utf-8")
    (assets_path / "app.js").write_text("window.ready = true;", encoding="utf-8")
    settings = Settings(
        database_path=tmp_path / "app.sqlite3",
        frontend_dist_path=frontend_path,
    )

    with TestClient(create_app(settings)) as client:
        index_response = client.get("/")
        report_route_response = client.get("/reports/report-1")
        asset_response = client.get("/assets/app.js")
        missing_asset_response = client.get("/assets/missing.js")
        health_response = client.get("/api/health")
        missing_api_response = client.get("/api/missing")

    assert index_response.status_code == 200
    assert index_response.text == "<h1>Compiled frontend</h1>"
    assert report_route_response.status_code == 200
    assert report_route_response.text == "<h1>Compiled frontend</h1>"
    assert asset_response.status_code == 200
    assert asset_response.text == "window.ready = true;"
    assert missing_asset_response.status_code == 404
    assert health_response.json()["status"] == "ok"
    assert missing_api_response.status_code == 404
