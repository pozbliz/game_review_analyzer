"""Provider-neutral execution result and failure contracts."""

from dataclasses import dataclass
from typing import Protocol

from game_review_analyzer.domain.analysis import AnalysisResult, OpinionExtractionResult


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


class AnalysisProviderError(RuntimeError):
    """Expose a stable non-secret provider failure code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code: str = code


class CancellationSignal(Protocol):
    """Allow provider work to observe cancellation without owning job state."""

    def is_set(self) -> bool:
        """Return whether cancellation was requested."""
