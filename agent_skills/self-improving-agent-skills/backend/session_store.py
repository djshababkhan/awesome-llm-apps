"""Keeps finished runs on disk so a restart cannot throw them away.

An optimization run costs many model calls and can take an hour, and its result
used to live only in the backend's memory. Restarting — which the dashboard's
own Restart button does — lost the improved skill before it could be
downloaded. Runs are written here when they finish and read back at startup.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(__file__).parent.parent / ".run" / "sessions"

# Session ids arrive over HTTP, so only a plain uuid-ish token may become a path.
SAFE_ID = re.compile(r"[a-zA-Z0-9_-]+")

# Everything the API needs to serve a finished run. Runtime objects such as the
# SSE queue are deliberately absent: they cannot be serialized and mean nothing
# to a later process.
PERSISTED_KEYS = (
    "skill_files",
    "file_list",
    "metadata",
    "scenarios",
    "evals",
    "status",
    "experiments",
    "activity",
    "error",
    "final_result",
    "current_skill_md",
    "original_skill_md",
    "created_at",
)


def _path_for(session_id: str) -> Path:
    if not SAFE_ID.fullmatch(session_id or ""):
        raise ValueError(f"Unsafe session id: {session_id!r}")
    return SESSIONS_DIR / f"{session_id}.json"


def save_session(session_id: str, session: dict) -> None:
    """Writes the durable part of a session. Failures are logged, never raised.

    A save is a courtesy to the next process; it must not take down the request
    that triggered it.
    """
    path = _path_for(session_id)
    saved = {key: session[key] for key in PERSISTED_KEYS if key in session}

    try:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        # Written beside the target first so a crash cannot leave a half file.
        pending = path.with_suffix(".pending")
        pending.write_text(json.dumps(saved), encoding="utf-8")
        pending.replace(path)
    except (OSError, TypeError, ValueError) as exc:
        logger.error(f"Could not save session {session_id}: {exc}")


def load_sessions() -> Dict[str, dict]:
    """Every session on disk. A file that will not parse is skipped, not fatal."""
    if not SESSIONS_DIR.is_dir():
        return {}

    sessions: Dict[str, dict] = {}
    for path in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            sessions[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning(f"Ignoring unreadable session file {path.name}: {exc}")
    return sessions


def forget_session(session_id: str) -> None:
    """Drops a session's file. Forgetting an unknown session is not an error."""
    try:
        _path_for(session_id).unlink(missing_ok=True)
    except (OSError, ValueError) as exc:
        logger.warning(f"Could not remove session {session_id}: {exc}")
