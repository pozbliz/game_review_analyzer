"""FastAPI application shell and its public health/configuration endpoints."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from game_review_analyzer.application.game_preview import (
    InvalidAppId,
    SteamMetadataSource,
    parse_app_id,
)
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.persistence.game_datasets import save_game_dataset
from game_review_analyzer.infrastructure.steam_metadata import (
    SteamGameNotFound,
    SteamMetadataMalformed,
    SteamMetadataUnavailable,
    SteamStoreMetadataAdapter,
)
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


def create_app(
    settings: Settings | None = None,
    metadata_source: SteamMetadataSource | None = None,
) -> FastAPI:
    """Create an application instance, optionally using test-specific settings."""

    resolved_settings = settings or Settings.from_environment()
    resolved_metadata_source = metadata_source or SteamStoreMetadataAdapter()

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

    @app.get(f"{API_PREFIX}/games/preview", response_model=SteamMetadata)
    def game_preview(appid: str) -> SteamMetadata:
        try:
            app_id: int = parse_app_id(appid)
            metadata: SteamMetadata = resolved_metadata_source.fetch(app_id)
            save_game_dataset(resolved_settings.database_path, metadata)
            return metadata
        except InvalidAppId as error:
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_app_id", "message": str(error)},
            ) from error
        except SteamGameNotFound as error:
            raise HTTPException(
                status_code=404,
                detail={"code": "game_not_found", "message": "Steam game not found"},
            ) from error
        except SteamMetadataMalformed as error:
            raise HTTPException(
                status_code=502,
                detail={"code": "invalid_steam_response", "message": "Steam returned invalid metadata"},
            ) from error
        except SteamMetadataUnavailable as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "steam_unavailable", "message": "Steam metadata is temporarily unavailable"},
            ) from error

    if resolved_settings.frontend_dist_path.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=resolved_settings.frontend_dist_path, html=True),
            name="frontend",
        )

    return app


app = create_app()
