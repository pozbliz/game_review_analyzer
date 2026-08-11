"""Behavior tests for the local application shell."""

from pathlib import Path

from fastapi.testclient import TestClient

from game_review_analyzer.infrastructure.persistence.database import (
    CURRENT_SCHEMA_VERSION,
    schema_version,
)
from game_review_analyzer.interfaces.http.app import create_app
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

    assert response.json() == {"environment": "test", "api_prefix": "/api"}
    assert "database_path" not in response.text


def test_shell_endpoints_publish_explicit_response_contracts(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "app.sqlite3")

    with TestClient(create_app(settings)) as client:
        schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert schemas["HealthResponse"]["required"] == ["status", "service"]
    assert schemas["PublicConfigResponse"]["required"] == ["environment", "api_prefix"]
