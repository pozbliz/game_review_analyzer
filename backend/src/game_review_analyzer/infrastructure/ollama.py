"""Discover and run models through the local Ollama HTTP API."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from game_review_analyzer.application.manual_codex import (
    MANUAL_CODEX_INSTRUCTIONS,
    ManualCodexValidationError,
    validate_analysis_result,
)
from game_review_analyzer.application.provider import (
    AnalysisProviderError,
    CancellationSignal,
    ProviderRun,
    ProviderUsage,
)
from game_review_analyzer.domain.analysis import AnalysisRequest, AnalysisResult


@dataclass(frozen=True)
class OllamaModel:
    """Describe one model already installed in the local Ollama store."""

    name: str
    size: int | None
    parameter_size: str | None
    quantization_level: str | None


@dataclass(frozen=True)
class OllamaStatus:
    """Expose local Ollama service readiness and installed models."""

    available: bool
    version: str | None
    models: tuple[OllamaModel, ...]


class OllamaError(AnalysisProviderError):
    """Expose a stable failure code for local Ollama analysis."""


JsonSource = Callable[[str], dict[str, Any]]
StreamSource = Callable[
    [dict[str, Any], CancellationSignal | None], Iterator[dict[str, Any]]
]


class OllamaProvider:
    """Run schema-constrained analysis using one explicitly selected local model."""

    def __init__(
        self,
        *,
        model: str,
        stream_source: StreamSource | None = None,
        max_attempts: int = 2,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.model: str = model
        self._stream_source: StreamSource = stream_source or _stream_generate
        self.max_attempts: int = max_attempts

    def analyze(
        self,
        request: AnalysisRequest,
        *,
        cancel_event: CancellationSignal | None = None,
    ) -> ProviderRun:
        """Generate and validate one result without changing or installing models."""

        for attempt in range(self.max_attempts):
            if cancel_event is not None and cancel_event.is_set():
                raise OllamaError("cancelled", "Ollama analysis was cancelled")
            response_text: str = ""
            final_event: dict[str, Any] = {}
            try:
                for event in self._stream_source(self._payload(request), cancel_event):
                    if cancel_event is not None and cancel_event.is_set():
                        raise OllamaError("cancelled", "Ollama analysis was cancelled")
                    if event.get("model") not in (None, self.model):
                        raise OllamaError(
                            "model_mismatch", "Ollama used a different model"
                        )
                    response_text += str(event.get("response", ""))
                    if event.get("done") is True:
                        final_event = event
                result: AnalysisResult = validate_analysis_result(
                    request, response_text, expected_provider="ollama"
                )
                if result.model != self.model:
                    raise OllamaError(
                        "model_mismatch", "Ollama result model does not match selection"
                    )
                return ProviderRun(
                    result=result,
                    usage=ProviderUsage(
                        input_tokens=_non_negative_int(
                            final_event.get("prompt_eval_count")
                        ),
                        cached_input_tokens=None,
                        output_tokens=_non_negative_int(final_event.get("eval_count")),
                    ),
                )
            except ManualCodexValidationError as error:
                if attempt + 1 == self.max_attempts:
                    raise OllamaError(
                        "invalid_result", "Ollama returned invalid analysis output"
                    ) from error
            except OllamaError:
                raise
            except TimeoutError as error:
                raise OllamaError(
                    "timeout", "Local Ollama exceeded the analysis time limit"
                ) from error
            except (OSError, URLError, json.JSONDecodeError) as error:
                raise OllamaError("unavailable", "Local Ollama is unavailable") from error
        raise AssertionError("unreachable")

    def _payload(self, request: AnalysisRequest) -> dict[str, Any]:
        return {
            "model": self.model,
            "prompt": (
                f"{MANUAL_CODEX_INSTRUCTIONS} Set provider to ollama and model to "
                f"{self.model}. Return only the schema-conforming JSON.\nREQUEST_JSON\n"
                f"{request.model_dump_json()}"
            ),
            "format": AnalysisResult.model_json_schema(),
            "stream": True,
            "think": False,
            "options": {"temperature": 0, "num_ctx": 16_384},
        }


def ollama_status(*, get_json: JsonSource | None = None) -> OllamaStatus:
    """List models exposed by the default local service without pulling anything."""

    source: JsonSource = get_json or _get_json
    try:
        version_payload: dict[str, Any] = source("/api/version")
        tags_payload: dict[str, Any] = source("/api/tags")
    except (OSError, URLError, TimeoutError, ValueError):
        return OllamaStatus(False, None, ())
    models: list[OllamaModel] = []
    for item in tags_payload.get("models", []):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        details: dict[str, Any] = (
            item.get("details") if isinstance(item.get("details"), dict) else {}
        )
        models.append(OllamaModel(
            name=item["name"],
            size=_non_negative_int(item.get("size")),
            parameter_size=_optional_string(details.get("parameter_size")),
            quantization_level=_optional_string(details.get("quantization_level")),
        ))
    version: str | None = _optional_string(version_payload.get("version"))
    return OllamaStatus(True, version, tuple(models))


def _get_json(path: str) -> dict[str, Any]:
    with urlopen(f"http://127.0.0.1:11434{path}", timeout=2) as response:
        payload: object = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Ollama returned a non-object response")
    return payload


def _stream_generate(
    payload: dict[str, Any], cancel_event: CancellationSignal | None
) -> Iterator[dict[str, Any]]:
    request = Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=600) as response:
        for line in response:
            if cancel_event is not None and cancel_event.is_set():
                response.close()
                raise OllamaError("cancelled", "Ollama analysis was cancelled")
            event: object = json.loads(line)
            if not isinstance(event, dict):
                raise json.JSONDecodeError("Expected object", str(event), 0)
            yield event


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _non_negative_int(value: object) -> int | None:
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else None
    )
