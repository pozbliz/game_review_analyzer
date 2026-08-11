"""FastAPI application shell and its public health/configuration endpoints."""

from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncIterator, Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from game_review_analyzer.application.game_preview import (
    InvalidAppId,
    SteamMetadataSource,
    parse_app_id,
)
from game_review_analyzer.application.game_catalog import (
    CatalogSource,
    FallbackSearchSource,
    search_games,
    synchronize_catalog,
)
from game_review_analyzer.application.report_exports import (
    export_report_csv,
    export_report_html,
    export_report_json,
    import_report_json,
)
from game_review_analyzer.application.storage_lifecycle import (
    DatabaseIntegrity,
    StorageDiagnostics,
    delete_game_dataset,
    delete_incomplete_job,
    delete_report_version,
    get_storage_diagnostics,
    verify_database_integrity,
)
from game_review_analyzer.domain.reports import ReportVersion
from game_review_analyzer.domain.game_catalog import CatalogSyncResult, GameSearchResult
from game_review_analyzer.domain.steam_metadata import SteamMetadata
from game_review_analyzer.infrastructure.persistence.database import initialize_database
from game_review_analyzer.infrastructure.job_runner import JobRunner, ReviewPageSource
from game_review_analyzer.infrastructure.persistence.game_datasets import (
    load_game_dataset,
    save_game_dataset,
)
from game_review_analyzer.infrastructure.persistence.jobs import (
    AnalysisJob,
    JobNotFound,
    ReconciliationResult,
    create_full_job,
    create_job,
    create_reconciliation_job,
    create_refresh_job,
    get_job,
    load_reconciliation_result,
    recoverable_job_ids,
    request_cancellation,
    retry_job,
)
from game_review_analyzer.infrastructure.persistence.report_versions import (
    ReportHistoryEntry,
    list_report_versions,
    load_report_version,
)
from game_review_analyzer.infrastructure.steam_metadata import (
    SteamGameNotFound,
    SteamMetadataMalformed,
    SteamMetadataUnavailable,
    SteamStoreMetadataAdapter,
)
from game_review_analyzer.infrastructure.steam_catalog import (
    SteamCatalogAdapter,
    SteamCatalogUnavailable,
    SteamStoreSearchAdapter,
)
from game_review_analyzer.infrastructure.steam_reviews import SteamReviewIngestionAdapter
from game_review_analyzer.shared.config import Settings
from game_review_analyzer.interfaces.http.reports import (
    ReportResponse,
    ThemeEvidenceResponse,
    build_report_response,
    build_theme_evidence_response,
)

API_PREFIX = "/api"


class HealthResponse(BaseModel):
    """Describe the stable backend health payload returned to API clients."""

    status: Literal["ok"]
    service: Literal["game-review-analyzer"]


class PublicConfigResponse(BaseModel):
    """Expose non-secret runtime configuration needed by the frontend."""

    environment: str
    api_prefix: Literal["/api"]
    steam_country_code: str
    keyed_catalog_available: bool


class QuickImportRequest(BaseModel):
    """Validate the user-selected review cap for one Quick import."""

    target_count: int = Field(default=5000, ge=1)


class DeletionRequest(BaseModel):
    """Require an explicit typed confirmation for one destructive operation."""

    confirmation: str = Field(min_length=1)


def create_app(
    settings: Settings | None = None,
    metadata_source: SteamMetadataSource | None = None,
    review_source: ReviewPageSource | None = None,
    catalog_source: CatalogSource | None = None,
    fallback_search_source: FallbackSearchSource | None = None,
) -> FastAPI:
    """Create an application instance, optionally using test-specific settings."""

    resolved_settings = settings or Settings.from_environment()
    resolved_metadata_source = metadata_source or SteamStoreMetadataAdapter(
        country_code=resolved_settings.steam_country_code
    )
    resolved_catalog_source = catalog_source or SteamCatalogAdapter()
    resolved_fallback_source = fallback_search_source or SteamStoreSearchAdapter()
    runner = JobRunner(
        resolved_settings.database_path,
        review_source or SteamReviewIngestionAdapter(),
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        initialize_database(resolved_settings.database_path)
        # ponytail: one import worker; increase only after measured parallel demand.
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="review-import")
        application.state.import_executor = executor
        for job_id in recoverable_job_ids(resolved_settings.database_path):
            executor.submit(runner.run, job_id)
        try:
            yield
        finally:
            executor.shutdown(wait=True)

    app = FastAPI(title="Game Review Analyzer", lifespan=lifespan)

    @app.get(f"{API_PREFIX}/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="game-review-analyzer")

    @app.get(f"{API_PREFIX}/config", response_model=PublicConfigResponse)
    def public_config() -> PublicConfigResponse:
        return PublicConfigResponse(
            environment=resolved_settings.environment,
            api_prefix=API_PREFIX,
            steam_country_code=resolved_settings.steam_country_code,
            keyed_catalog_available=bool(resolved_settings.steam_web_api_key),
        )

    @app.post(f"{API_PREFIX}/catalog/sync", response_model=CatalogSyncResult)
    def sync_catalog() -> CatalogSyncResult:
        if not resolved_settings.steam_web_api_key:
            raise HTTPException(status_code=409, detail={"code": "steam_key_required"})
        try:
            return synchronize_catalog(
                resolved_settings.database_path,
                resolved_catalog_source,
                resolved_settings.steam_web_api_key,
            )
        except SteamCatalogUnavailable as error:
            raise HTTPException(
                status_code=503, detail={"code": "steam_catalog_unavailable"}
            ) from error

    @app.get(f"{API_PREFIX}/games/search", response_model=tuple[GameSearchResult, ...])
    def game_search(q: str) -> tuple[GameSearchResult, ...]:
        try:
            return search_games(
                resolved_settings.database_path,
                resolved_fallback_source,
                q,
                resolved_settings.steam_country_code,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail={"code": "invalid_search_query"}
            ) from error
        except SteamCatalogUnavailable as error:
            raise HTTPException(
                status_code=503, detail={"code": "steam_search_unavailable"}
            ) from error

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

    def submit(job_id: str) -> None:
        app.state.import_executor.submit(runner.run, job_id)

    def existing_job(job_id: str) -> AnalysisJob:
        try:
            return get_job(resolved_settings.database_path, job_id)
        except JobNotFound as error:
            raise HTTPException(status_code=404, detail={"code": "job_not_found"}) from error

    @app.post(
        f"{API_PREFIX}/games/{{app_id}}/imports/quick",
        response_model=AnalysisJob,
        status_code=202,
    )
    def start_quick_import(app_id: int, request: QuickImportRequest) -> AnalysisJob:
        if load_game_dataset(resolved_settings.database_path, app_id) is None:
            raise HTTPException(status_code=404, detail={"code": "game_not_found"})
        job: AnalysisJob = create_job(
            resolved_settings.database_path,
            app_id,
            request.target_count,
        )
        submit(job.id)
        return job

    @app.post(
        f"{API_PREFIX}/games/{{app_id}}/imports/full",
        response_model=AnalysisJob,
        status_code=202,
    )
    def start_full_import(app_id: int) -> AnalysisJob:
        if load_game_dataset(resolved_settings.database_path, app_id) is None:
            raise HTTPException(status_code=404, detail={"code": "game_not_found"})
        job: AnalysisJob = create_full_job(resolved_settings.database_path, app_id)
        submit(job.id)
        return job

    @app.post(
        f"{API_PREFIX}/games/{{app_id}}/reconciliations",
        response_model=AnalysisJob,
        status_code=202,
    )
    def start_reconciliation(app_id: int) -> AnalysisJob:
        if load_game_dataset(resolved_settings.database_path, app_id) is None:
            raise HTTPException(status_code=404, detail={"code": "game_not_found"})
        try:
            job: AnalysisJob = create_reconciliation_job(
                resolved_settings.database_path, app_id
            )
        except ValueError as error:
            raise HTTPException(
                status_code=409, detail={"code": "reconciliation_requires_reviews"}
            ) from error
        submit(job.id)
        return job

    @app.get(
        f"{API_PREFIX}/reconciliations/{{job_id}}",
        response_model=ReconciliationResult,
    )
    def reconciliation_result(job_id: str) -> ReconciliationResult:
        try:
            return load_reconciliation_result(resolved_settings.database_path, job_id)
        except ValueError as error:
            raise HTTPException(
                status_code=404, detail={"code": "reconciliation_not_found"}
            ) from error

    @app.post(
        f"{API_PREFIX}/games/{{app_id}}/refreshes",
        response_model=AnalysisJob,
        status_code=202,
    )
    def start_refresh(app_id: int, request: QuickImportRequest) -> AnalysisJob:
        if load_game_dataset(resolved_settings.database_path, app_id) is None:
            raise HTTPException(status_code=404, detail={"code": "game_not_found"})
        try:
            job: AnalysisJob = create_refresh_job(
                resolved_settings.database_path, app_id, request.target_count
            )
        except ValueError as error:
            raise HTTPException(
                status_code=409, detail={"code": "refresh_requires_reviews"}
            ) from error
        submit(job.id)
        return job

    @app.get(
        f"{API_PREFIX}/games/{{app_id}}/reports",
        response_model=tuple[ReportHistoryEntry, ...],
    )
    def report_history(app_id: int) -> tuple[ReportHistoryEntry, ...]:
        if load_game_dataset(resolved_settings.database_path, app_id) is None:
            raise HTTPException(status_code=404, detail={"code": "game_not_found"})
        return list_report_versions(resolved_settings.database_path, app_id)

    @app.get(f"{API_PREFIX}/reports/{{report_version_id}}", response_model=ReportResponse)
    def report_summary(report_version_id: str) -> ReportResponse:
        report = load_report_version(resolved_settings.database_path, report_version_id)
        if report is None:
            raise HTTPException(status_code=404, detail={"code": "report_not_found"})
        return build_report_response(resolved_settings.database_path, report)

    @app.get(
        f"{API_PREFIX}/reports/{{report_version_id}}/themes/{{theme_id}}/evidence",
        response_model=ThemeEvidenceResponse,
    )
    def theme_evidence(
        report_version_id: str,
        theme_id: str,
    ) -> ThemeEvidenceResponse:
        report = load_report_version(resolved_settings.database_path, report_version_id)
        if report is None:
            raise HTTPException(status_code=404, detail={"code": "report_not_found"})
        response: ThemeEvidenceResponse | None = build_theme_evidence_response(
            resolved_settings.database_path, report, theme_id
        )
        if response is None:
            raise HTTPException(status_code=404, detail={"code": "theme_not_found"})
        return response

    @app.get(f"{API_PREFIX}/reports/{{report_version_id}}/export")
    def download_report(
        report_version_id: str,
        format: Literal["html", "json", "csv"],
        include_full_review_text: bool = False,
    ) -> Response:
        exporters = {
            "html": (export_report_html, "text/html", "html"),
            "json": (export_report_json, "application/json", "json"),
            "csv": (export_report_csv, "text/csv", "csv"),
        }
        exporter, media_type, extension = exporters[format]
        try:
            if format == "html":
                content: str = exporter(
                    resolved_settings.database_path, report_version_id
                )
            else:
                content = exporter(
                    resolved_settings.database_path,
                    report_version_id,
                    include_full_review_text=include_full_review_text,
                )
        except ValueError as error:
            raise HTTPException(
                status_code=404, detail={"code": "report_not_found"}
            ) from error
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="report-export.{extension}"'
            },
        )

    @app.post(
        f"{API_PREFIX}/reports/import",
        response_model=ReportResponse,
        status_code=201,
    )
    async def import_report(request: Request) -> ReportResponse:
        try:
            payload: str = (await request.body()).decode("utf-8")
            report: ReportVersion = import_report_json(
                resolved_settings.database_path, payload
            )
        except UnicodeDecodeError as error:
            raise HTTPException(
                status_code=422, detail={"code": "invalid_report_export"}
            ) from error
        except ValueError as error:
            code: str = (
                "invalid_report_export"
                if str(error) == "Invalid report export"
                else "report_import_conflict"
            )
            raise HTTPException(
                status_code=422 if code == "invalid_report_export" else 409,
                detail={"code": code, "message": str(error)},
            ) from error
        return build_report_response(resolved_settings.database_path, report)

    @app.get(f"{API_PREFIX}/storage", response_model=StorageDiagnostics)
    def storage_diagnostics() -> StorageDiagnostics:
        return get_storage_diagnostics(resolved_settings.database_path)

    @app.get(f"{API_PREFIX}/storage/integrity", response_model=DatabaseIntegrity)
    def storage_integrity() -> DatabaseIntegrity:
        return verify_database_integrity(resolved_settings.database_path)

    @app.post(
        f"{API_PREFIX}/reports/{{report_version_id}}/delete",
        status_code=204,
    )
    def delete_report(report_version_id: str, request: DeletionRequest) -> Response:
        try:
            delete_report_version(
                resolved_settings.database_path,
                report_version_id,
                request.confirmation,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=409, detail={"code": "deletion_rejected", "message": str(error)}
            ) from error
        return Response(status_code=204)

    @app.post(f"{API_PREFIX}/jobs/{{job_id}}/delete", status_code=204)
    def delete_job(job_id: str, request: DeletionRequest) -> Response:
        try:
            delete_incomplete_job(
                resolved_settings.database_path, job_id, request.confirmation
            )
        except ValueError as error:
            raise HTTPException(
                status_code=409, detail={"code": "deletion_rejected", "message": str(error)}
            ) from error
        return Response(status_code=204)

    @app.post(f"{API_PREFIX}/games/{{app_id}}/delete", status_code=204)
    def delete_game(app_id: int, request: DeletionRequest) -> Response:
        try:
            delete_game_dataset(
                resolved_settings.database_path, app_id, request.confirmation
            )
        except ValueError as error:
            raise HTTPException(
                status_code=409, detail={"code": "deletion_rejected", "message": str(error)}
            ) from error
        return Response(status_code=204)

    @app.get(f"{API_PREFIX}/jobs/{{job_id}}", response_model=AnalysisJob)
    def job_progress(job_id: str) -> AnalysisJob:
        return existing_job(job_id)

    @app.post(f"{API_PREFIX}/jobs/{{job_id}}/cancel", response_model=AnalysisJob)
    def cancel_job(job_id: str) -> AnalysisJob:
        existing_job(job_id)
        request_cancellation(resolved_settings.database_path, job_id)
        return get_job(resolved_settings.database_path, job_id)

    @app.post(
        f"{API_PREFIX}/jobs/{{job_id}}/retry",
        response_model=AnalysisJob,
        status_code=202,
    )
    def retry_failed_job(job_id: str) -> AnalysisJob:
        existing_job(job_id)
        try:
            job: AnalysisJob = retry_job(resolved_settings.database_path, job_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail={"code": "job_not_retryable"}) from error
        submit(job.id)
        return job

    if resolved_settings.frontend_dist_path.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=resolved_settings.frontend_dist_path, html=True),
            name="frontend",
        )

    return app


app = create_app()
