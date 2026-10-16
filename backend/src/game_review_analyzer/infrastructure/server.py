"""Detached local server supervision and exclusive database ownership."""

import argparse
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import socket
import signal
import subprocess
import sys
import time
import uuid
from typing import Iterator


class OwnershipConflict(RuntimeError):
    """Report an active process already owning the requested database or supervisor."""


class JobLimits(ctypes.Structure):
    """Match the Windows basic job limits used by SetInformationJobObject."""
    _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
                ("flags", wintypes.DWORD), ("minimum", ctypes.c_size_t),
                ("maximum", ctypes.c_size_t), ("process_limit", wintypes.DWORD),
                ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                ("scheduling", wintypes.DWORD)]


class ExtendedJobLimits(ctypes.Structure):
    """Match Windows extended limits; use kill-on-close to own descendants."""
    _fields_ = [("basic", JobLimits), ("io", ctypes.c_ulonglong * 6),
                ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]


@contextmanager
def owned_process_tree(child: subprocess.Popen[bytes], job_name: str | None = None) -> Iterator[None]:
    """Kill surviving descendants when a Windows child exits or is stopped."""
    if os.name != "nt":
        try:
            yield
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel.CreateJobObjectW(None, job_name)
    if not job:
        raise OSError("Cannot create owned process job")
    try:
        limits = ExtendedJobLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise OSError("Cannot configure owned process job")
        # A named job stays empty until real Python joins: an existing outer job
        # cannot join a nonempty sibling job after its venv launcher was assigned.
        if job_name is None:
            process = kernel.OpenProcess(0x0101, False, child.pid)  # SET_QUOTA | TERMINATE
            if not process:
                raise OSError("Cannot open owned child")
            try:
                if not kernel.AssignProcessToJobObject(job, process):
                    raise OSError("Cannot assign owned child to job")
            finally:
                kernel.CloseHandle(process)
        yield
    finally:
        kernel.CloseHandle(job)


def join_owner_job(job_name: str) -> None:
    """Join from the serving interpreter before it can create provider processes."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenJobObjectW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.OpenJobObjectW.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel.OpenJobObjectW(5, False, job_name)  # ASSIGN_PROCESS | QUERY
    if not job:
        raise OSError("Cannot open owner job")
    try:
        member = wintypes.BOOL()
        process = kernel.GetCurrentProcess()
        if not kernel.IsProcessInJob(process, job, ctypes.byref(member)):
            raise OSError("Cannot query owner job")
        if not member.value and not kernel.AssignProcessToJobObject(job, process):
            raise OSError(ctypes.get_last_error(), "Cannot join owner job")
    finally:
        kernel.CloseHandle(job)


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    """Hold an OS lock; process exit releases it without stale PID cleanup."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise OwnershipConflict("Database or supervisor already in use") from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def serve(port: int, database: Path) -> int:
    """Reserve the port before application startup can recover durable work."""
    with socket.socket() as listener:
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            listener.bind(("127.0.0.1", port))
            listener.listen(128)
        except OSError:
            return 2
        os.environ["GAME_REVIEW_ANALYZER_DATABASE"] = str(database)
        try:
            import uvicorn
            from game_review_analyzer.interfaces.http.app import app
        except Exception as error:
            database.parent.mkdir(parents=True, exist_ok=True)
            diagnostic: RotatingFileHandler = RotatingFileHandler(
                f"{database}.server-startup.log", maxBytes=1_000_000, backupCount=3
            )
            diagnostic.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            try:
                diagnostic.emit(logging.LogRecord(
                    "server-startup", logging.ERROR, __file__, 0,
                    "startup_failed stage=import_configuration error_type=%s",
                    (type(error).__name__,), None,
                ))
            finally:
                diagnostic.close()
            return 4
        server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False))
        server.run(sockets=[listener])
        if server.started:
            return 0
        return 3 if getattr(app.state, "startup_error_type", "") == "OwnershipConflict" else 4


def stop_child(child: subprocess.Popen[bytes]) -> None:
    """Terminate only the child tree created by this supervisor."""
    if child.poll() is None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def supervise(port: int, database: Path, restart_limit: int = 3) -> int:
    """Restart unexpected exits with bounded backoff; a marker requests stop."""
    stop_path: Path = Path(f"{database}.server.stop")
    with exclusive_lock(Path(f"{database}.supervisor.lock")):
        stop_path.unlink(missing_ok=True)
        logger: logging.Logger = logging.getLogger("server-lifecycle")
        logger.setLevel(logging.INFO)
        handler: RotatingFileHandler = RotatingFileHandler(f"{database}.server.log", maxBytes=1_000_000, backupCount=3)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
        try:
            for attempt in range(restart_limit + 1):
                job_name: str = f"Local\\GameReviewAnalyzer-{uuid.uuid4()}"
                owner_arguments: list[str] = ["--owner-job", job_name] if os.name == "nt" else []
                child: subprocess.Popen[bytes] = subprocess.Popen([
                    sys.executable, "-m", "game_review_analyzer.infrastructure.server",
                    "--serve", "--wait-for-owner", "--port", str(port),
                    "--database", str(database), *owner_arguments,
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   stdin=subprocess.PIPE, start_new_session=os.name != "nt")
                logger.info("started child_pid=%s port=%s attempt=%s", child.pid, port, attempt)
                try:
                    try:
                        with owned_process_tree(child, job_name):
                            assert child.stdin is not None
                            try:
                                child.stdin.write(b"1")
                                child.stdin.close()
                            except BrokenPipeError:
                                pass
                            while child.poll() is None and not stop_path.exists():
                                time.sleep(0.2)
                    except OSError:
                        logger.error("startup_refused reason=process_ownership_failed")
                        return 4
                    if stop_path.exists():
                        logger.info("stop_requested child_pid=%s", child.pid)
                        return 0
                    logger.info("child_exited child_pid=%s exit_code=%s", child.pid, child.returncode)
                    if child.returncode in (2, 3, 4):
                        reason: str = {2: "port_in_use", 3: "database_in_use", 4: "startup_failed"}[child.returncode]
                        logger.error("startup_refused reason=%s", reason)
                        return child.returncode
                    if attempt < restart_limit:
                        delay: int = min(2 ** attempt, 8)
                        logger.info("restart_scheduled delay_seconds=%s", delay)
                        deadline: float = time.monotonic() + delay
                        while time.monotonic() < deadline:
                            if stop_path.exists():
                                return 0
                            time.sleep(0.2)
                finally:
                    stop_child(child)
            logger.error("restart_limit_exhausted limit=%s", restart_limit)
            return 1
        finally:
            handler.close()
            logger.removeHandler(handler)


def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    mode: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--serve", action="store_true")
    mode.add_argument("--supervise", action="store_true")
    mode.add_argument("--stop", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--wait-for-owner", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--owner-job", help=argparse.SUPPRESS)
    arguments: argparse.Namespace = parser.parse_args()
    if not 1 <= arguments.port <= 65535:
        parser.error("port must be between 1 and 65535")
    database: Path = arguments.database.resolve()
    if arguments.stop:
        lock_path: Path = Path(f"{database}.supervisor.lock")
        if not lock_path.exists():
            print("No supervisor owns this database.")
            return 3
        try:
            with exclusive_lock(lock_path):
                print("No supervisor owns this database.")
                return 3
        except OwnershipConflict:
            Path(f"{database}.server.stop").touch()
        deadline: float = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                with exclusive_lock(lock_path):
                    print("Supervisor and owned server stopped.")
                    return 0
            except OwnershipConflict:
                time.sleep(0.2)
        print("Stop was requested, but the supervisor did not stop within 30 seconds.")
        return 1
    try:
        if arguments.wait_for_owner and sys.stdin.buffer.read(1) != b"1":
            return 4
        if arguments.owner_job:
            try:
                join_owner_job(arguments.owner_job)
            except OSError:
                return 4
        return serve(arguments.port, database) if arguments.serve else supervise(arguments.port, database)
    except OwnershipConflict:
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
