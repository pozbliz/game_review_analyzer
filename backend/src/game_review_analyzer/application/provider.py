"""Provider-neutral execution result and failure contracts."""

from dataclasses import dataclass
from collections.abc import Iterable
from hashlib import sha256
import json
from typing import Any, Protocol

from game_review_analyzer.domain.analysis import (
    AnalysisResult,
    ANALYSIS_CONTRACT_VERSION,
    AnalysisSourceReview,
    OpinionExtractionResult,
    ThemeAnalysisRequest,
    ThemeAnalysisResult,
)


def build_theme_analysis_request(
    request_id: str,
    app_id: int,
    game_title: str,
    reviews: Iterable[AnalysisSourceReview],
) -> ThemeAnalysisRequest:
    """Create a Version 3 request bound to its ordered full-text scope."""

    source_reviews: tuple[AnalysisSourceReview, ...] = tuple(reviews)
    scope_data: dict[str, Any] = {
        "app_id": app_id,
        "game_title": game_title,
        "reviews": [review.model_dump(mode="json") for review in source_reviews],
    }
    canonical_scope: str = json.dumps(
        scope_data,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return ThemeAnalysisRequest(
        schema_version=ANALYSIS_CONTRACT_VERSION,
        request_id=request_id,
        scope_sha256=sha256(canonical_scope.encode("utf-8")).hexdigest(),
        app_id=app_id,
        game_title=game_title,
        reviews=source_reviews,
    )


@dataclass(frozen=True)
class ProviderUsage:
    """Report measured tokens when an analysis provider exposes them."""

    input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class ProviderRun:
    """Return one validated provider result and its measured usage."""

    result: AnalysisResult
    usage: ProviderUsage


@dataclass(frozen=True)
class ExtractionProviderRun:
    """Return one validated bounded extraction result and measured usage."""

    result: OpinionExtractionResult
    usage: ProviderUsage


@dataclass(frozen=True)
class ThemeProviderRun:
    """Return one validated Theme candidate result and measured usage."""

    result: ThemeAnalysisResult
    usage: ProviderUsage


def validate_theme_provider_result(
    request: ThemeAnalysisRequest,
    result: ThemeAnalysisResult,
    *,
    expected_provider: str,
    expected_model: str,
) -> None:
    """Validate one Theme result against its exact request and provenance."""

    if result.request_id != request.request_id or result.scope_sha256 != request.scope_sha256:
        raise ValueError("Theme result does not match its request")
    requested_ids: tuple[str, ...] = tuple(
        review.review_revision_id for review in request.reviews
    )
    if (
        len(result.completed_review_revision_ids) != len(requested_ids)
        or set(result.completed_review_revision_ids) != set(requested_ids)
    ):
        raise ValueError("Theme result does not complete the exact review scope")
    if result.provider != expected_provider or result.model != expected_model:
        raise ValueError("Theme result provenance does not match the selected provider")


class AnalysisProviderError(RuntimeError):
    """Expose a stable non-secret provider failure code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code: str = code


class CancellationSignal(Protocol):
    """Allow provider work to observe cancellation without owning job state."""

    def is_set(self) -> bool:
        """Return whether cancellation was requested."""
