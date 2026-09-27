"""Small OpenTelemetry and structured-event helpers."""

import json
import logging
import os
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


def configure_telemetry(app: FastAPI) -> None:
    """Instrument HTTP requests and optionally export traces through OTLP/HTTP."""

    global _configured
    LOGGER.setLevel(logging.INFO)
    endpoint: str | None = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint and not _configured:
        provider = TracerProvider(
            resource=Resource.create({"service.name": "game-review-analyzer"})
        )
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        _configured = True
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/api/health")


def log_event(event: str, **fields: Any) -> None:
    """Write one machine-readable event; callers must pass only non-sensitive fields."""

    LOGGER.info(json.dumps({"event": event, **fields}, separators=(",", ":")))
