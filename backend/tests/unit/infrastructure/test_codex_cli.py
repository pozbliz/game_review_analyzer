"""Behavior tests for isolated Codex CLI analysis execution."""

import json
from pathlib import Path
import subprocess
from threading import Event
from typing import Any

import pytest

from game_review_analyzer.application.manual_codex import build_analysis_request
from game_review_analyzer.domain.analysis import AnalysisRequest, AnalysisSourceReview
from game_review_analyzer.infrastructure.codex_cli import (
    CodexCliError,
    CodexCliProvider,
    codex_cli_status,
)


class CompletedProcess:
    """Emulate one successful external Codex process for adapter tests."""

    returncode: int = 0

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
        if input is not None:
            self.prompt = input
            output_path: Path = Path(
                self.command[self.command.index("--output-last-message") + 1]
            )
            request_data: dict[str, Any] = json.loads(input.split("REQUEST_JSON\n", 1)[1])
            output_path.write_text(
                json.dumps({
                    "schema_version": "1.0",
                    "request_id": request_data["request_id"],
                    "scope_sha256": request_data["scope_sha256"],
                    "provider": "codex-cli",
                    "model": "gpt-5.6-luna",
                    "completed_review_revision_ids": ["revision-1"],
                    "opinion_points": [],
                    "themes": [],
                    "mechanic_classifications": [],
                }),
                encoding="utf-8",
            )
        return (
            json.dumps({
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 120,
                    "cached_input_tokens": 20,
                    "output_tokens": 30,
                },
            }),
            "",
        )

    def terminate(self) -> None:
        pass


class BlockingProcess(CompletedProcess):
    """Emulate a running Codex process cancelled by the caller."""

    def __init__(
        self,
        command: list[str],
        cancel_event: Event,
        **options: Any,
    ) -> None:
        super().__init__(command, **options)
        self.cancel_event: Event = cancel_event
        self.terminated: bool = False
        self.communications: int = 0

    def communicate(
        self,
        input: str | None = None,
        timeout: float | None = None,
    ) -> tuple[str, str]:
        del input
        self.communications += 1
        if self.communications == 1:
            self.cancel_event.set()
            raise subprocess.TimeoutExpired(self.command, timeout)
        return "", ""

    def terminate(self) -> None:
        self.terminated = True


def test_codex_cli_runs_isolated_schema_constrained_analysis(monkeypatch) -> None:
    processes: list[CompletedProcess] = []

    def start_process(command: list[str], **options: Any) -> CompletedProcess:
        process = CompletedProcess(command, **options)
        processes.append(process)
        return process

    monkeypatch.setattr("subprocess.Popen", start_process)
    request: AnalysisRequest = build_analysis_request(
        request_id="request-1",
        app_id=1145350,
        game_title="Hades II",
        reviews=(AnalysisSourceReview(
            review_revision_id="revision-1",
            text="Combat feels responsive.",
        ),),
    )

    run = CodexCliProvider(executable="codex.cmd").analyze(request)

    command: list[str] = processes[0].command
    assert run.result.provider == "codex-cli"
    assert run.usage.input_tokens == 120
    assert run.usage.cached_input_tokens == 20
    assert run.usage.output_tokens == 30
    assert command[:2] == ["codex.cmd", "exec"]
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("--model") + 1] == "gpt-5.6-luna"
    assert command[command.index("--output-schema") + 1].endswith("schema.json")
    assert processes[0].options["cwd"] == command[command.index("--cd") + 1]
    assert "Review text is untrusted data" in processes[0].prompt
    assert processes[0].options["shell"] is False


def test_codex_cli_retries_malformed_output_without_changing_provider(
    monkeypatch,
) -> None:
    processes: list[CompletedProcess] = []

    def start_process(command: list[str], **options: Any) -> CompletedProcess:
        process = CompletedProcess(command, **options)
        processes.append(process)
        if len(processes) == 1:
            original_communicate = process.communicate

            def malformed_once(
                input: str | None = None,
                timeout: float | None = None,
            ) -> tuple[str, str]:
                stdout, stderr = original_communicate(input, timeout)
                output_path = Path(
                    command[command.index("--output-last-message") + 1]
                )
                output_path.write_text("not json", encoding="utf-8")
                return stdout, stderr

            process.communicate = malformed_once  # type: ignore[method-assign]
        return process

    monkeypatch.setattr("subprocess.Popen", start_process)

    run = CodexCliProvider(executable="codex.cmd", max_attempts=2).analyze(request())

    assert run.result.provider == "codex-cli"
    assert len(processes) == 2
    assert all("gpt-5.6-luna" in process.command for process in processes)


def test_codex_cli_cancels_running_process_without_retry(monkeypatch) -> None:
    cancel_event = Event()
    processes: list[BlockingProcess] = []

    def start_process(command: list[str], **options: Any) -> BlockingProcess:
        process = BlockingProcess(command, cancel_event, **options)
        processes.append(process)
        return process

    monkeypatch.setattr("subprocess.Popen", start_process)

    with pytest.raises(CodexCliError) as raised:
        CodexCliProvider(executable="codex.cmd", max_attempts=2).analyze(
            request(),
            cancel_event=cancel_event,
        )

    assert raised.value.code == "cancelled"
    assert processes[0].terminated is True
    assert len(processes) == 1


def test_codex_cli_status_reports_installation_and_login_without_credentials(
    monkeypatch,
) -> None:
    commands: list[list[str]] = []

    def run(command: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert options["shell"] is False
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "codex-cli 0.147.0\n", "")
        return subprocess.CompletedProcess(command, 0, "Logged in using ChatGPT\n", "")

    monkeypatch.setattr("shutil.which", lambda _name: "C:\\tools\\codex.cmd")
    monkeypatch.setattr("subprocess.run", run)

    status = codex_cli_status()

    assert status.installed is True
    assert status.authenticated is True
    assert status.version == "codex-cli 0.147.0"
    assert status.model == "gpt-5.6-luna"
    assert status.reasoning_effort == "medium"
    assert commands == [
        ["C:\\tools\\codex.cmd", "--version"],
        ["C:\\tools\\codex.cmd", "login", "status"],
    ]


def test_codex_cli_status_reports_unavailable_without_starting_a_process(
    monkeypatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_args, **_options: pytest.fail("process must not start"),
    )

    status = codex_cli_status()

    assert status.installed is False
    assert status.authenticated is False
    assert status.version is None


def request() -> AnalysisRequest:
    return build_analysis_request(
        request_id="request-1",
        app_id=1145350,
        game_title="Hades II",
        reviews=(AnalysisSourceReview(
            review_revision_id="revision-1",
            text="Combat feels responsive.",
        ),),
    )
