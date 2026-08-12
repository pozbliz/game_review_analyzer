"""Run provider-neutral analysis through an authenticated local Codex CLI."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from typing import Any

from game_review_analyzer.application.manual_codex import (
    MANUAL_CODEX_INSTRUCTIONS,
    ManualCodexValidationError,
    validate_analysis_result,
)
from game_review_analyzer.domain.analysis import AnalysisRequest, AnalysisResult
from game_review_analyzer.application.provider import (
    AnalysisProviderError,
    CancellationSignal,
    ProviderRun,
    ProviderUsage,
)


CodexCliUsage = ProviderUsage
CodexCliRun = ProviderRun


@dataclass(frozen=True)
class CodexCliStatus:
    """Describe non-secret Codex CLI readiness for provider selection."""

    installed: bool
    authenticated: bool
    version: str | None
    model: str
    reasoning_effort: str


class CodexCliError(AnalysisProviderError):
    """Expose a stable non-secret failure code for one Codex CLI run."""

class CodexCliProvider:
    """Execute one isolated analysis using the user's existing Codex CLI login."""

    def __init__(
        self,
        *,
        executable: str,
        model: str = "gpt-5.6-luna",
        reasoning_effort: str = "medium",
        max_attempts: int = 2,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.executable: str = executable
        self.model: str = model
        self.reasoning_effort: str = reasoning_effort
        self.max_attempts: int = max_attempts

    def analyze(
        self,
        request: AnalysisRequest,
        *,
        cancel_event: CancellationSignal | None = None,
    ) -> CodexCliRun:
        """Run Codex and validate its final JSON against the exact review scope."""

        for attempt in range(self.max_attempts):
            if cancel_event is not None and cancel_event.is_set():
                raise CodexCliError("cancelled", "Codex CLI analysis was cancelled")
            try:
                result_json, stdout = self._run_once(request, cancel_event)
                result: AnalysisResult = validate_analysis_result(
                    request,
                    result_json,
                    expected_provider="codex-cli",
                )
                if result.model != self.model:
                    raise CodexCliError(
                        "model_mismatch",
                        "Codex CLI result model does not match the selected model",
                    )
                return CodexCliRun(result=result, usage=self._usage(stdout))
            except ManualCodexValidationError as error:
                if attempt + 1 == self.max_attempts:
                    raise CodexCliError(
                        error.code,
                        "Codex CLI returned invalid analysis output",
                    ) from error
            except CodexCliError as error:
                if error.code == "cancelled" or attempt + 1 == self.max_attempts:
                    raise
        raise AssertionError("unreachable")

    def _run_once(
        self,
        request: AnalysisRequest,
        cancel_event: CancellationSignal | None,
    ) -> tuple[str, str]:
        with TemporaryDirectory(prefix="game-review-analyzer-codex-") as directory:
            working_directory: Path = Path(directory)
            schema_path: Path = working_directory / "schema.json"
            output_path: Path = working_directory / "result.json"
            schema_path.write_text(
                json.dumps(AnalysisResult.model_json_schema()),
                encoding="utf-8",
            )
            command: list[str] = [
                self.executable,
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--model",
                self.model,
                "--cd",
                str(working_directory),
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "--json",
                "-c",
                f'model_reasoning_effort="{self.reasoning_effort}"',
                "-",
            ]
            options: dict[str, Any] = {
                "cwd": str(working_directory),
                "stdin": subprocess.PIPE,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "encoding": "utf-8",
                "shell": False,
            }
            if os.name == "nt":
                options["creationflags"] = subprocess.CREATE_NO_WINDOW
            process: subprocess.Popen[str] = subprocess.Popen(command, **options)
            prompt: str | None = self._prompt(request)
            while True:
                try:
                    stdout, _stderr = process.communicate(
                        input=prompt,
                        timeout=0.1,
                    )
                    break
                except subprocess.TimeoutExpired:
                    prompt = None
                    if cancel_event is not None and cancel_event.is_set():
                        process.terminate()
                        try:
                            process.communicate(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.communicate()
                        raise CodexCliError(
                            "cancelled",
                            "Codex CLI analysis was cancelled",
                        )
            if process.returncode != 0 or not output_path.is_file():
                raise CodexCliError("process_failed", "Codex CLI analysis failed")
            result_json: str = output_path.read_text(encoding="utf-8")
            return result_json, stdout

    def _prompt(self, request: AnalysisRequest) -> str:
        return (
            f"{MANUAL_CODEX_INSTRUCTIONS} Set provider to codex-cli and model to "
            f"{self.model}. Return only the schema-conforming JSON.\nREQUEST_JSON\n"
            f"{request.model_dump_json()}"
        )

    @staticmethod
    def _usage(stdout: str) -> CodexCliUsage:
        usage: dict[str, Any] = {}
        for line in stdout.splitlines():
            try:
                event: dict[str, Any] = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if event.get("type") == "turn.completed" and isinstance(
                event.get("usage"), dict
            ):
                usage = event["usage"]
        return CodexCliUsage(
            input_tokens=_non_negative_int(usage.get("input_tokens")),
            cached_input_tokens=_non_negative_int(usage.get("cached_input_tokens")),
            output_tokens=_non_negative_int(usage.get("output_tokens")),
        )


def _non_negative_int(value: object) -> int | None:
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else None
    )


def codex_cli_status(
    *,
    model: str = "gpt-5.6-luna",
    reasoning_effort: str = "medium",
) -> CodexCliStatus:
    """Check installation and login without reading or returning credential data."""

    executable: str | None = shutil.which("codex")
    if executable is None:
        return CodexCliStatus(False, False, None, model, reasoning_effort)
    options: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "timeout": 5,
        "shell": False,
    }
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        version_process: subprocess.CompletedProcess[str] = subprocess.run(
            [executable, "--version"],
            **options,
        )
        login_process: subprocess.CompletedProcess[str] = subprocess.run(
            [executable, "login", "status"],
            **options,
        )
    except (OSError, subprocess.SubprocessError):
        return CodexCliStatus(True, False, None, model, reasoning_effort)
    version: str | None = (
        version_process.stdout.strip() if version_process.returncode == 0 else None
    )
    return CodexCliStatus(
        installed=True,
        authenticated=login_process.returncode == 0,
        version=version or None,
        model=model,
        reasoning_effort=reasoning_effort,
    )
