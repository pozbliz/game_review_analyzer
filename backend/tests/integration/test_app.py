"""Behavior tests for the local application shell."""

from pathlib import Path

from fastapi.testclient import TestClient

from game_review_analyzer.infrastructure.persistence.database import (
    CURRENT_SCHEMA_VERSION,
    schema_version,
)
from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.infrastructure.codex_cli import CodexCliStatus
from game_review_analyzer.infrastructure.ollama import OllamaModel, OllamaStatus
from game_review_analyzer.shared.config import Settings


def test_health_endpoint_reports_ready_service(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "game-review-analyzer"}


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


def test_ollama_status_lists_installed_local_models_without_download_controls(
    tmp_path: Path,
) -> None:
    status = OllamaStatus(
        available=True,
        version="0.12.6",
        models=(OllamaModel("qwen3.5:4b", 3_400_000_000, "4B", "Q4_K_M"),),
    )
    with TestClient(create_app(
        Settings(database_path=tmp_path / "app.sqlite3"),
        ollama_status_source=lambda: status,
    )) as client:
        response = client.get("/api/providers/ollama")

    assert response.status_code == 200
    assert response.json() == {
        "available": True,
        "version": "0.12.6",
        "processing_location": "local_device",
        "models": [{
            "name": "qwen3.5:4b",
            "size": 3_400_000_000,
            "parameter_size": "4B",
            "quantization_level": "Q4_K_M",
        }],
    }
    assert "pull" not in response.text.lower()


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
        asset_response = client.get("/assets/app.js")
        health_response = client.get("/api/health")

    assert index_response.status_code == 200
    assert index_response.text == "<h1>Compiled frontend</h1>"
    assert asset_response.status_code == 200
    assert asset_response.text == "window.ready = true;"
    assert health_response.json()["status"] == "ok"
