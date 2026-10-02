"""Behavior tests for Version 3 Codex CLI execution."""

import json
from pathlib import Path
import subprocess
from typing import Any

import pytest

from game_review_analyzer.application.provider import build_theme_merge_request
from game_review_analyzer.domain.analysis import (
    AnalysisSourceReview,
    ThemeAnalysisRequest,
    ThemeMergeCandidate,
)
from game_review_analyzer.infrastructure.codex_cli import (
    CodexCliError,
    CodexCliProvider,
    codex_cli_status,
)


class CompletedProcess:
    """Emulate one successful external Codex process."""

    returncode: int = 0
    pid: int = 999_999

    def __init__(self, command: list[str], **options: Any) -> None:
        self.command: list[str] = command
        self.options: dict[str, Any] = options
        self.prompt: str = ""

    def communicate(
        self,
        input: str | None = None,
        timeout: float | None = None,
    ) -> tuple[str, str]:
        del timeout
        assert input is not None
        self.prompt = input
        output_path = Path(
            self.command[self.command.index("--output-last-message") + 1]
        )
        if "Merge semantically equivalent" in input:
            result: dict[str, object] = {
                "new_themes": [
                    {
                        "title": "Responsive combat",
                        "summary": "Players praise responsive combat.",
                        "polarity": "positive",
                    }
                ],
                "assignments": [
                    {
                        "established_theme_position": None,
                        "new_theme_position": 0,
                    }
                ],
            }
        else:
            result = {
                "themes": [
                    {
                        "title": "Responsive combat",
                        "summary": "Players praise responsive combat.",
                        "polarity": "positive",
                        "supporting_review_positions": [0],
                    }
                ]
            }
        output_path.write_text(json.dumps(result), encoding="utf-8")
        usage: dict[str, object] = {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 120,
                "cached_input_tokens": 20,
                "output_tokens": 30,
            },
        }
        return json.dumps(usage), ""

    def terminate(self) -> None:
        pass


def test_codex_cli_runs_isolated_theme_analysis(monkeypatch) -> None:
    processes: list[CompletedProcess] = []

    def start_process(command: list[str], **options: Any) -> CompletedProcess:
        process = CompletedProcess(command, **options)
        processes.append(process)
        return process

    monkeypatch.setattr("subprocess.Popen", start_process)

    run = CodexCliProvider(executable="codex.cmd").analyze_themes(theme_request())

    command: list[str] = processes[0].command
    assert run.result.completed_review_revision_ids == ("revision-1",)
    assert run.result.themes[0].supporting_review_revision_ids == ("revision-1",)
    assert run.usage.input_tokens == 120
    assert command[:2] == ["codex.cmd", "exec"]
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "Return no excerpts" in processes[0].prompt
    assert processes[0].options["shell"] is False


def test_codex_cli_binds_semantic_merge_output_locally(monkeypatch) -> None:
    monkeypatch.setattr("subprocess.Popen", CompletedProcess)
    request = build_theme_merge_request(
        "merge-1",
        1145350,
        "Hades II",
        (
            ThemeMergeCandidate(
                candidate_key="batch-1:responsive-combat",
                title="Responsive combat",
                summary="Players praise responsive combat.",
                polarity="positive",
                supporting_review_revision_ids=("revision-1",),
            ),
        ),
    )

    run = CodexCliProvider(executable="codex.cmd").merge_themes(request)

    assert run.result.themes[0].theme_id == "merge-1:theme:1"
    assert run.result.assignments[0].candidate_key == "batch-1:responsive-combat"
    assert run.result.assignments[0].theme_id == "merge-1:theme:1"


def test_codex_cli_retries_invalid_theme_output(monkeypatch) -> None:
    processes: list[CompletedProcess] = []

    def start_process(command: list[str], **options: Any) -> CompletedProcess:
        process = CompletedProcess(command, **options)
        original_communicate = process.communicate

        if not processes:
            def malformed(
                input: str | None = None,
                timeout: float | None = None,
            ) -> tuple[str, str]:
                stdout, stderr = original_communicate(input, timeout)
                output_path = Path(command[command.index("--output-last-message") + 1])
                output_path.write_text("not json", encoding="utf-8")
                return stdout, stderr

            process.communicate = malformed  # type: ignore[method-assign]
        processes.append(process)
        return process

    monkeypatch.setattr("subprocess.Popen", start_process)

    run = CodexCliProvider(executable="codex.cmd").analyze_themes(theme_request())

    assert run.result.themes[0].title == "Responsive combat"
    assert len(processes) == 2
    assert "invalid_theme_result" in processes[1].prompt


def test_codex_cli_classifies_failure_without_exposing_stderr(monkeypatch) -> None:
    class FailedProcess(CompletedProcess):
        returncode: int = 1

        def communicate(
            self,
            input: str | None = None,
            timeout: float | None = None,
        ) -> tuple[str, str]:
            del input, timeout
            return "", "429 rate limit; review text must stay private"

    monkeypatch.setattr("subprocess.Popen", FailedProcess)

    with pytest.raises(CodexCliError) as raised:
        CodexCliProvider(executable="codex.cmd", max_attempts=1).analyze_themes(
            theme_request()
        )

    assert raised.value.code == "provider_rate_limited"
    assert "review text" not in str(raised.value)


def test_codex_cli_status_reports_login_without_credentials(monkeypatch) -> None:
    commands: list[list[str]] = []

    def run(command: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert options["shell"] is False
        stdout: str = "codex-cli 0.147.0\n" if "--version" in command else "Logged in using ChatGPT\n"
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr("shutil.which", lambda _name: "C:\\tools\\codex.cmd")
    monkeypatch.setattr("subprocess.run", run)

    status = codex_cli_status()

    assert (status.installed, status.authenticated) == (True, True)
    assert status.version == "codex-cli 0.147.0"
    assert commands[-1] == ["C:\\tools\\codex.cmd", "login", "status"]


def theme_request() -> ThemeAnalysisRequest:
    return ThemeAnalysisRequest(
        schema_version="3.1",
        request_id="request-3",
        scope_sha256="b" * 64,
        app_id=1145350,
        game_title="Hades II",
        reviews=(
            AnalysisSourceReview(
                review_revision_id="revision-1",
                text="Combat feels responsive.",
            ),
        ),
    )
