"""Exercise exclusive startup through the application's actual lifespan."""

from pathlib import Path
import os
import re
import socket
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.request

import pytest
from fastapi.testclient import TestClient

from game_review_analyzer.interfaces.http.app import create_app
from game_review_analyzer.shared.config import Settings
from game_review_analyzer.infrastructure import server


def test_database_has_one_active_application_and_releases_after_shutdown(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "exclusive.sqlite3")
    with TestClient(create_app(settings)) as first:
        assert first.get("/api/health").status_code == 200
        with pytest.raises(RuntimeError, match="already in use"):
            with TestClient(create_app(settings)):
                pass
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get("/api/health").status_code == 200


def test_supervisor_restarts_crashed_server_and_stops_owned_tree(tmp_path: Path) -> None:
    """Use an empty DB: startup must never call Steam or Codex."""
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    database = tmp_path / "process.sqlite3"
    command = [sys.executable, "-m", "game_review_analyzer.infrastructure.server"]
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    supervisor = subprocess.Popen(command + ["--supervise", "--port", str(port),
                                             "--database", str(database)], env=environment)
    stop_path = Path(f"{database}.server.stop")
    log_path = Path(f"{database}.server.log")

    def wait_ready() -> None:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            assert supervisor.poll() is None, "Supervisor exited before readiness"
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        raise AssertionError("Server did not become ready")

    try:
        wait_ready()
        duplicate = subprocess.run(command + ["--supervise", "--port", str(port + 1),
                                               "--database", str(database)], env=environment, timeout=10)
        assert duplicate.returncode == 3
        other_app = subprocess.run(command + ["--serve", "--port", str(port + 1),
                                               "--database", str(database)], env=environment, timeout=10)
        assert other_app.returncode == 3
        original_pid = int(re.findall(r"started child_pid=(\d+)", log_path.read_text())[0])
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(original_pid), "/T", "/F"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal
            os.kill(original_pid, signal.SIGKILL)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if len(re.findall(r"started child_pid=(\d+)", log_path.read_text())) == 2:
                break
            time.sleep(0.1)
        wait_ready()
        assert "exit_code=" in log_path.read_text()
        assert "restart_scheduled" in log_path.read_text()
        stopped = subprocess.run(command + ["--stop", "--database", str(database)],
                                 env=environment, timeout=15)
        assert stopped.returncode == 0
        assert supervisor.wait(timeout=15) == 0
        assert "stop_requested" in log_path.read_text()
        with pytest.raises((OSError, urllib.error.URLError)):
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.5)
    finally:
        stop_path.touch()
        try:
            supervisor.wait(timeout=15)
        except subprocess.TimeoutExpired:
            supervisor.kill()
            supervisor.wait()


def test_occupied_port_refuses_before_database_initialization(tmp_path: Path) -> None:
    database = tmp_path / "must-not-exist.sqlite3"
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        port = occupied.getsockname()[1]
        result = subprocess.run([
            sys.executable, "-m", "game_review_analyzer.infrastructure.server", "--supervise",
            "--port", str(port), "--database", str(database),
        ], env=environment, timeout=10)
    assert result.returncode == 2
    assert not database.exists()
    events = Path(f"{database}.server.log").read_text()
    assert events.count("started child_pid=") == 1
    assert "startup_refused reason=port_in_use" in events


def test_stop_without_supervisor_does_not_create_stop_marker(tmp_path: Path) -> None:
    database = tmp_path / "not-started.sqlite3"
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    result = subprocess.run([sys.executable, "-m", "game_review_analyzer.infrastructure.server",
                             "--stop", "--database", str(database)], env=environment, timeout=10)
    assert result.returncode == 3
    assert not Path(f"{database}.server.stop").exists()


def test_import_configuration_failure_records_safe_error_type(tmp_path: Path) -> None:
    database = tmp_path / "invalid-config.sqlite3"
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
                       GAME_REVIEW_ANALYZER_STEAM_COUNTRY="invalid-private-value")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    result = subprocess.run([sys.executable, "-m", "game_review_analyzer.infrastructure.server",
                             "--supervise", "--port", str(port), "--database", str(database)],
                            env=environment, timeout=10)
    assert result.returncode == 4
    diagnostic = Path(f"{database}.server-startup.log").read_text()
    assert "stage=import_configuration" in diagnostic
    assert "error_type=ValueError" in diagnostic
    assert "invalid-private-value" not in diagnostic


@pytest.mark.skipif(os.name != "nt", reason="Windows launch wrapper")
def test_launch_wrapper_honors_database_environment(tmp_path: Path) -> None:
    """Intercept only Start-Process; never start the default production database."""
    import json
    project = Path(__file__).resolve().parents[3]
    captured = tmp_path / "arguments.json"
    probe = tmp_path / "probe.ps1"
    probe.write_text("""
param($Wrapper, $Capture, $Database)
function Start-Process {
    param($FilePath, $ArgumentList, $WorkingDirectory, $WindowStyle, [switch]$PassThru)
    $ArgumentList | ConvertTo-Json | Set-Content -LiteralPath $Capture
    $result = [pscustomobject]@{HasExited=$false}
    $result | Add-Member -MemberType ScriptMethod -Name Refresh -Value {}
    return $result
}
function Start-Sleep {param($Seconds)}
if ($Database) { & $Wrapper -Database $Database } else { & $Wrapper }
""")
    environment = dict(os.environ, GAME_REVIEW_ANALYZER_DATABASE="data/environment-choice.sqlite3")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                             "-File", str(probe), str(project / "scripts/start-app.ps1"), str(captured)],
                            env=environment, cwd=tmp_path, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr.decode()
    arguments = json.loads(captured.read_text(encoding="utf-8-sig"))
    assert arguments[-1] == f'"{project / "backend/data/environment-choice.sqlite3"}"'
    explicit = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                               "-File", str(probe), str(project / "scripts/start-app.ps1"),
                               str(captured), "explicit-choice.sqlite3"],
                              env=environment, cwd=tmp_path, capture_output=True, timeout=15)
    assert explicit.returncode == 0, explicit.stderr.decode()
    arguments = json.loads(captured.read_text(encoding="utf-8-sig"))
    assert arguments[-1] == f'"{tmp_path / "explicit-choice.sqlite3"}"'


def test_clean_unrequested_exit_restarts_but_exhausts_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace only the child process boundary with a real clean-exit process."""
    spawn = subprocess.Popen
    monkeypatch.setattr(server.subprocess, "Popen", lambda *args, **kwargs:
                        spawn([sys.executable, "-c", "raise SystemExit(0)"], **kwargs))
    database = tmp_path / "clean-exit.sqlite3"
    assert server.supervise(8000, database, restart_limit=1) == 1
    events = Path(f"{database}.server.log").read_text()
    assert events.count("started child_pid=") == 2
    assert events.count("exit_code=0") == 2
    assert "restart_limit_exhausted limit=1" in events


def test_startup_failure_releases_database_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from game_review_analyzer.interfaces.http import app as app_module
    settings = Settings(database_path=tmp_path / "failed-startup.sqlite3")
    initialize = app_module.initialize_database

    def fail_startup(path: Path) -> None:
        raise ValueError("invalid startup")

    monkeypatch.setattr(app_module, "initialize_database", fail_startup)
    with pytest.raises(ValueError, match="invalid startup"):
        with TestClient(create_app(settings)):
            pass
    monkeypatch.setattr(app_module, "initialize_database", initialize)
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get("/api/health").status_code == 200


@pytest.mark.skipif(os.name != "nt", reason="Windows job ownership")
def test_real_serving_interpreter_joins_named_job_after_redirector_race(tmp_path: Path) -> None:
    import ctypes
    from ctypes import wintypes
    import json
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    job_name = f"Local\\GameReviewAnalyzer-test-{uuid.uuid4()}"
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    child = subprocess.Popen([sys.executable, "-m", "game_review_analyzer.infrastructure.server",
                              "--serve", "--wait-for-owner", "--owner-job", job_name,
                              "--port", str(port), "--database", str(tmp_path / "serve.sqlite3")],
                             stdin=subprocess.PIPE, env=environment)
    time.sleep(0.75)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenJobObjectW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.OpenJobObjectW.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    try:
        with server.owned_process_tree(child, job_name):
            assert child.stdin is not None
            child.stdin.write(b"1")
            child.stdin.close()
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                assert child.poll() is None
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.5):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise AssertionError("Serving interpreter did not become ready")
            probe = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                    f"@(Get-CimInstance Win32_Process -Filter 'ParentProcessId = {child.pid}' | "
                                    "Select-Object -ExpandProperty ProcessId) | ConvertTo-Json -Compress"],
                                   capture_output=True, check=True, timeout=15)
            serving_pid = json.loads(probe.stdout.decode("utf-8-sig"))
            if isinstance(serving_pid, list):
                serving_pid = serving_pid[0]
            process = kernel.OpenProcess(0x1000, False, serving_pid)
            job = kernel.OpenJobObjectW(4, False, job_name)
            try:
                member = wintypes.BOOL()
                assert process and job
                assert kernel.IsProcessInJob(process, job, ctypes.byref(member))
                assert member.value
            finally:
                kernel.CloseHandle(process)
                kernel.CloseHandle(job)
        child.wait(timeout=10)
        with pytest.raises(OSError):
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.5)
    finally:
        server.stop_child(child)


@pytest.mark.skipif(os.name != "nt", reason="Windows job ownership")
def test_owned_job_kills_provider_descendant_after_server_crash(tmp_path: Path) -> None:
    import ctypes
    from ctypes import wintypes
    pid_file = tmp_path / "descendant.pid"
    job_name = f"Local\\GameReviewAnalyzer-test-{uuid.uuid4()}"
    script = (
        "import os,subprocess,sys,time; sys.stdin.buffer.read(1); "
        "from game_review_analyzer.infrastructure.server import join_owner_job; join_owner_job(sys.argv[2]); "
        "join_owner_job(sys.argv[2]); "  # Already in this job; membership must skip reassignment.
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
        "open(sys.argv[1],'w').write(str(child.pid)); time.sleep(0.5); os._exit(9)"
    )
    child = subprocess.Popen([sys.executable, "-c", script, str(pid_file), job_name], stdin=subprocess.PIPE)
    time.sleep(0.75)  # Let the venv redirector spawn real Python before job assignment.
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    descendant_handle = None
    try:
        with server.owned_process_tree(child, job_name):
            assert child.stdin is not None
            child.stdin.write(b"1")
            child.stdin.close()
            deadline = time.monotonic() + 10
            while not pid_file.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            descendant_pid = int(pid_file.read_text())
            descendant_handle = kernel.OpenProcess(0x100000, False, descendant_pid)
            assert descendant_handle
            assert child.wait(timeout=10) == 9
            assert kernel.WaitForSingleObject(descendant_handle, 0) == 258  # Still running
        assert kernel.WaitForSingleObject(descendant_handle, 5000) == 0  # Job closed, descendant exited
    finally:
        if descendant_handle:
            subprocess.run(["taskkill", "/PID", str(descendant_pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            kernel.CloseHandle(descendant_handle)
        server.stop_child(child)
