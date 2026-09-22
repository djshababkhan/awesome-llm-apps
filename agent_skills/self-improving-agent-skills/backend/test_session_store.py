"""Tests that finished runs survive a backend restart.

An optimization run costs many model calls and can take an hour. Until now the
result lived only in memory, so restarting the backend — which the dashboard's
own Restart button does — threw the improved skill away before it could be
downloaded.

    python test_session_store.py
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import session_store
from session_store import load_sessions, save_session, forget_session

SESSION = {
    "skill_files": {"SKILL.md": "# original"},
    "file_list": ["SKILL.md"],
    "metadata": {"name": "demo"},
    "scenarios": [{"id": 1}],
    "evals": [{"id": 1}],
    "status": "complete",
    "experiments": [{"experiment_id": 1}],
    "final_result": {"final_score": 100.0},
    "current_skill_md": "# improved",
    "original_skill_md": "# original",
    "created_at": 1_700_000_000.0,
}


def with_store():
    """Points the store at a throwaway directory, returning a restore callable."""
    previous = session_store.SESSIONS_DIR
    temp = tempfile.TemporaryDirectory()
    session_store.SESSIONS_DIR = Path(temp.name) / "sessions"

    def restore():
        session_store.SESSIONS_DIR = previous
        temp.cleanup()

    return restore


def test_a_saved_session_comes_back():
    restore = with_store()
    try:
        save_session("abc", SESSION)
        restored = load_sessions()
        assert "abc" in restored, restored.keys()
        assert restored["abc"]["current_skill_md"] == "# improved"
        assert restored["abc"]["final_result"]["final_score"] == 100.0
    finally:
        restore()


def test_the_downloadable_files_survive():
    """download_skill needs skill_files plus current_skill_md to build the zip."""
    restore = with_store()
    try:
        save_session("abc", SESSION)
        restored = load_sessions()["abc"]
        assert restored["skill_files"] == SESSION["skill_files"]
        assert restored["current_skill_md"] == SESSION["current_skill_md"]
    finally:
        restore()


def test_runtime_objects_are_not_saved():
    """A queue or task cannot be serialized and must not break the save."""
    restore = with_store()
    try:
        live = dict(SESSION, event_queue=asyncio.Queue(), task=object())
        save_session("abc", live)
        restored = load_sessions()["abc"]
        assert "event_queue" not in restored
        assert "task" not in restored
    finally:
        restore()


def test_saving_twice_keeps_the_newer_result():
    restore = with_store()
    try:
        save_session("abc", SESSION)
        save_session("abc", dict(SESSION, current_skill_md="# improved again"))
        assert load_sessions()["abc"]["current_skill_md"] == "# improved again"
    finally:
        restore()


def test_no_saved_sessions_is_not_an_error():
    restore = with_store()
    try:
        assert load_sessions() == {}
    finally:
        restore()


def test_a_corrupt_file_does_not_lose_the_others():
    restore = with_store()
    try:
        save_session("good", SESSION)
        session_store.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        (session_store.SESSIONS_DIR / "broken.json").write_text("{not json")
        restored = load_sessions()
        assert "good" in restored, "one bad file must not take the rest down"
        assert "broken" not in restored
    finally:
        restore()


def test_forgetting_a_session_removes_its_file():
    restore = with_store()
    try:
        save_session("abc", SESSION)
        forget_session("abc")
        assert load_sessions() == {}
        forget_session("abc")  # Forgetting twice is not an error.
    finally:
        restore()


def test_session_ids_cannot_escape_the_store_directory():
    """Session ids come in over HTTP, so they must never build a path upwards."""
    restore = with_store()
    try:
        for bad in ("../escape", "a/b", ""):
            try:
                save_session(bad, SESSION)
            except ValueError:
                continue
            raise AssertionError(f"expected ValueError for {bad!r}")
    finally:
        restore()


def test_saved_file_is_readable_json():
    restore = with_store()
    try:
        save_session("abc", SESSION)
        raw = json.loads((session_store.SESSIONS_DIR / "abc.json").read_text())
        assert raw["status"] == "complete"
    finally:
        restore()


def main():
    tests = [
        test_a_saved_session_comes_back,
        test_the_downloadable_files_survive,
        test_runtime_objects_are_not_saved,
        test_saving_twice_keeps_the_newer_result,
        test_no_saved_sessions_is_not_an_error,
        test_a_corrupt_file_does_not_lose_the_others,
        test_forgetting_a_session_removes_its_file,
        test_session_ids_cannot_escape_the_store_directory,
        test_saved_file_is_readable_json,
    ]

    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}\n     {exc}")
        else:
            print(f"PASS {test.__name__}")

    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
