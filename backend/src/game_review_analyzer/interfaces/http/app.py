"""FastAPI application shell and its public health/configuration endpoints."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.shared.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application instance, optionally using test-specific settings."""

    resolved_settings = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        initialize_database(resolved_settings.database_path)
        yield

    app = FastAPI(title="Game Review Analyzer", lifespan=lifespan)

    @app.get(f"{resolved_settings.api_prefix}/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "game-review-analyzer"}

    @app.get(f"{resolved_settings.api_prefix}/config")
    def public_config() -> dict[str, str]:
        return {
            "environment": resolved_settings.environment,
            "api_prefix": resolved_settings.api_prefix,
        }

    return app


app = create_app()
