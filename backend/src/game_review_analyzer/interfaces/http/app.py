"""FastAPI application shell and its public health/configuration endpoints."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal

from fastapi import FastAPI
from pydantic import BaseModel

from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.shared.config import Settings


class HealthResponse(BaseModel):
    """Describe the stable backend health payload returned to API clients."""

    status: Literal["ok"]
    service: Literal["game-review-analyzer"]


class PublicConfigResponse(BaseModel):
    """Expose non-secret runtime configuration needed by the frontend."""

    environment: str
    api_prefix: str


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application instance, optionally using test-specific settings."""

    resolved_settings = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        initialize_database(resolved_settings.database_path)
        yield

    app = FastAPI(title="Game Review Analyzer", lifespan=lifespan)

    @app.get(f"{resolved_settings.api_prefix}/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="game-review-analyzer")

    @app.get(f"{resolved_settings.api_prefix}/config", response_model=PublicConfigResponse)
    def public_config() -> PublicConfigResponse:
        return PublicConfigResponse(
            environment=resolved_settings.environment,
            api_prefix=resolved_settings.api_prefix,
        )

    return app


app = create_app()
