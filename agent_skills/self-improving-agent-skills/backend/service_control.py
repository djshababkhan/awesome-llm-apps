"""Hands restart and shutdown requests from the API to the start.sh supervisor.

The backend cannot restart itself: the process serving the request is the one
being replaced. So a request is written to a file in the run directory, and the
supervisor loop in start.sh picks it up and cycles the servers. The supervisor
advertises itself with a pid file, which lets the UI tell "nothing is watching"
apart from "the request was accepted".
"""

import os
from pathlib import Path
from typing import Optional

RUN_DIR = Path(__file__).parent.parent / ".run"
SUPERVISOR_PID_FILE_NAME = "supervisor.pid"
REQUEST_FILE_NAME = "request"

# Plain words rather than JSON: the supervisor reads these from bash.
VALID_ACTIONS = ("restart", "shutdown")


def _supervisor_pid_file() -> Path:
    return RUN_DIR / SUPERVISOR_PID_FILE_NAME


def _request_file() -> Path:
    return RUN_DIR / REQUEST_FILE_NAME


def _read(path: Path) -> Optional[str]:
    """File contents stripped of whitespace, or None when absent or unreadable."""
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def supervisor_pid() -> Optional[int]:
    """The pid start.sh recorded, or None when there is no readable pid file."""
    raw = _read(_supervisor_pid_file())
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def is_supervised() -> bool:
    """Whether a live start.sh supervisor is watching for control requests."""
    pid = supervisor_pid()
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        # Stale pid file from a supervisor that exited without cleaning up.
        return False
    return True


def request_action(action: str) -> None:
    """Asks the supervisor to restart or shut down the stack.

    Raises ValueError for anything outside VALID_ACTIONS, so an unexpected value
    can never reach the supervisor's shell.
    """
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unknown service action: {action!r}")

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    # Written to a neighbour first so the supervisor never reads a partial file.
    pending = _request_file().with_suffix(".pending")
    pending.write_text(f"{action}\n", encoding="utf-8")
    pending.replace(_request_file())


def pending_request() -> Optional[str]:
    """The action awaiting the supervisor, or None when there is none."""
    return _read(_request_file())


def clear_request() -> None:
    """Drops any pending request. Clearing when there is none is not an error."""
    _request_file().unlink(missing_ok=True)
