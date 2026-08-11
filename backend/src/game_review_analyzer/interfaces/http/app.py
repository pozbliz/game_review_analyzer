"""FastAPI application shell and its public health/configuration endpoints."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.shared.config import Settings

API_PREFIX = "/api"


class HealthResponse(BaseModel):
    """Describe the stable backend health payload returned to API clients."""

    status: Literal["ok"]
    service: Literal["game-review-analyzer"]


class PublicConfigResponse(BaseModel):
    """Expose non-secret runtime configuration needed by the frontend."""

    environment: str
    api_prefix: Literal["/api"]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application instance, optionally using test-specific settings."""

    resolved_settings = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        initialize_database(resolved_settings.database_path)
        yield

    app = FastAPI(title="Game Review Analyzer", lifespan=lifespan)

    @app.get(f"{API_PREFIX}/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="game-review-analyzer")

    @app.get(f"{API_PREFIX}/config", response_model=PublicConfigResponse)
    def public_config() -> PublicConfigResponse:
        return PublicConfigResponse(
            environment=resolved_settings.environment,
            api_prefix=API_PREFIX,
        )

    if resolved_settings.frontend_dist_path.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=resolved_settings.frontend_dist_path, html=True),
            name="frontend",
        )

    return app


app = create_app()
