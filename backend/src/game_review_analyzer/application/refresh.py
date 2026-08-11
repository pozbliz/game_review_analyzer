"""Build an exact provider request from a completed refresh checkpoint."""

from pathlib import Path

from game_review_analyzer.application.manual_codex import build_analysis_request
from game_review_analyzer.domain.analysis import AnalysisRequest, AnalysisSourceReview
from game_review_analyzer.domain.reviews import SteamReview
from game_review_analyzer.infrastructure.persistence.game_datasets import load_game_dataset
from game_review_analyzer.infrastructure.persistence.jobs import (
    AnalysisJob,
    get_job,
    load_job_analysis_scope,
)
from game_review_analyzer.infrastructure.persistence.review_revisions import (
    load_review_revisions_by_ids,
)


def build_refresh_analysis_request(
    database_path: Path,
    job_id: str,
    request_id: str,
) -> AnalysisRequest:
    """Bind reanalysis to the latest exact revision for each retained review."""

    job: AnalysisJob = get_job(database_path, job_id)
    revision_ids: tuple[int, ...] | None = load_job_analysis_scope(
        database_path, job_id
    )
    if job.scope != "refresh" or job.state != "completed" or revision_ids is None:
        raise ValueError("Refresh must complete before reanalysis")
    metadata = load_game_dataset(database_path, job.app_id)
    if metadata is None:
        raise ValueError("Matching Game Dataset metadata is unavailable")
    revisions: dict[int, SteamReview] = load_review_revisions_by_ids(
        database_path, revision_ids
    )
    return build_analysis_request(
        request_id=request_id,
        app_id=job.app_id,
        game_title=metadata.title,
        reviews=(
            AnalysisSourceReview(
                review_revision_id=revisions[revision_id].review_id,
                text=revisions[revision_id].text,
            )
            for revision_id in revision_ids
        ),
    )
