"""Small OpenTelemetry and structured-event helpers."""

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


LOGGER = logging.getLogger("game_review_analyzer")
TRACER = trace.get_tracer("game_review_analyzer")
_configured: bool = False
_event_log_path: Path | None = None
_SENSITIVE_FIELDS: frozenset[str] = frozenset({
    "credential",
    "credentials",
    "api_key",
    "model_output",
    "prompt",
    "review_text",
    "stderr",
})


def configure_event_log(
    log_path: Path,
    *,
    max_bytes: int = 1_000_000,
    backup_count: int = 3,
) -> None:
    """Write structured events to one bounded local JSON-lines log."""

    global _event_log_path
    resolved_path: Path = log_path.resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    for handler in tuple(LOGGER.handlers):
        if getattr(handler, "game_review_analyzer_event_log", False):
            LOGGER.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(
        resolved_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    setattr(handler, "game_review_analyzer_event_log", True)
    LOGGER.addHandler(handler)
    _event_log_path = resolved_path


def configure_telemetry(app: FastAPI, database_path: Path) -> Path:
    """Instrument HTTP requests and optionally export traces through OTLP/HTTP."""

    global _configured
    LOGGER.setLevel(logging.INFO)
    log_path: Path = database_path.with_suffix(".log")
    configure_event_log(log_path)
    endpoint: str | None = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint and not _configured:
        provider = TracerProvider(
            resource=Resource.create({"service.name": "game-review-analyzer"})
        )
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        _configured = True
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/api/health")
    return log_path


def log_event(event: str, *, level: str = "info", **fields: Any) -> None:
    """Write one machine-readable event; callers must pass only non-sensitive fields."""

    safe_fields: dict[str, Any] = {
        key: value for key, value in fields.items() if key not in _SENSITIVE_FIELDS
    }
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        **safe_fields,
    }
    log_method = getattr(LOGGER, level, LOGGER.info)
    log_method(json.dumps(payload, separators=(",", ":"), default=str))


def read_events(
    log_path: Path | None = None,
    *,
    limit: int = 200,
) -> tuple[dict[str, Any], ...]:
    """Read recent valid structured events from the bounded local log."""

    if limit < 1:
        return ()
    resolved_path: Path | None = (log_path or _event_log_path)
    if resolved_path is None:
        return ()
    paths: tuple[Path, ...] = tuple(
        path
        for path in (
            resolved_path.with_name(f"{resolved_path.name}.3"),
            resolved_path.with_name(f"{resolved_path.name}.2"),
            resolved_path.with_name(f"{resolved_path.name}.1"),
            resolved_path,
        )
        if path.is_file()
    )
    events: list[dict[str, Any]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                event: Any = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
    return tuple(events[-limit:])
