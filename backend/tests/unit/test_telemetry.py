"""Persistent redacted diagnostics tests."""

from pathlib import Path

from game_review_analyzer.shared.telemetry import (
    configure_event_log,
    log_event,
    read_events,
)


def test_event_log_persists_structured_events_without_sensitive_payloads(
    tmp_path: Path,
) -> None:
    log_path: Path = tmp_path / "app.log"
    configure_event_log(log_path)

    log_event(
        "analysis.failed",
        level="error",
        run_id="run-1",
        error_code="theme_scope_incomplete",
        prompt="private review content",
    )

    assert read_events(log_path) == ({
        "timestamp": read_events(log_path)[0]["timestamp"],
        "level": "error",
        "event": "analysis.failed",
        "run_id": "run-1",
        "error_code": "theme_scope_incomplete",
    },)
    assert "review text" not in log_path.read_text(encoding="utf-8")
    assert "private review content" not in log_path.read_text(encoding="utf-8")


def test_event_log_returns_only_the_requested_recent_events(tmp_path: Path) -> None:
    log_path: Path = tmp_path / "app.log"
    configure_event_log(log_path)
    for position in range(3):
        log_event("diagnostic.event", position=position)

    assert [event["position"] for event in read_events(log_path, limit=2)] == [1, 2]
