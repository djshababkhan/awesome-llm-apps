"""Tests for the restart/shutdown request file shared with the start.sh supervisor.

    python test_service_control.py
"""

import os
import sys
import tempfile
from pathlib import Path

import service_control
from service_control import (
    VALID_ACTIONS,
    clear_request,
    is_supervised,
    pending_request,
    request_action,
    supervisor_pid,
)

LIVE_PID = os.getpid()
DEAD_PID = 2 ** 22  # Far above any pid macOS or Linux hands out.


def with_run_dir():
    """Points the module at a throwaway run directory, returning a restore callable."""
    previous = service_control.RUN_DIR
    temp = tempfile.TemporaryDirectory()
    service_control.RUN_DIR = Path(temp.name)

    def restore():
        service_control.RUN_DIR = previous
        temp.cleanup()

    return restore


def write_supervisor_pid(pid):
    (service_control.RUN_DIR / "supervisor.pid").write_text(f"{pid}\n")


def test_no_supervisor_when_pid_file_is_missing():
    restore = with_run_dir()
    try:
        assert supervisor_pid() is None
        assert is_supervised() is False
    finally:
        restore()


def test_supervised_when_pid_file_names_a_live_process():
    restore = with_run_dir()
    try:
        write_supervisor_pid(LIVE_PID)
        assert supervisor_pid() == LIVE_PID
        assert is_supervised() is True
    finally:
        restore()


def test_stale_pid_file_does_not_count_as_supervised():
    restore = with_run_dir()
    try:
        write_supervisor_pid(DEAD_PID)
        assert is_supervised() is False
    finally:
        restore()


def test_unreadable_pid_file_does_not_count_as_supervised():
    restore = with_run_dir()
    try:
        write_supervisor_pid("not-a-pid")
        assert supervisor_pid() is None
        assert is_supervised() is False
    finally:
        restore()


def test_request_action_writes_the_action_for_the_supervisor():
    restore = with_run_dir()
    try:
        request_action("restart")
        assert pending_request() == "restart"
    finally:
        restore()


def test_request_action_creates_the_run_directory():
    restore = with_run_dir()
    try:
        nested = service_control.RUN_DIR / "missing"
        service_control.RUN_DIR = nested
        request_action("shutdown")
        assert pending_request() == "shutdown"
    finally:
        restore()


def test_latest_request_replaces_the_previous_one():
    restore = with_run_dir()
    try:
        request_action("restart")
        request_action("shutdown")
        assert pending_request() == "shutdown"
    finally:
        restore()


def test_unknown_action_is_rejected():
    restore = with_run_dir()
    try:
        for action in ("reboot", "", "  ", "restart; rm -rf /"):
            try:
                request_action(action)
            except ValueError:
                continue
            raise AssertionError(f"expected ValueError for {action!r}")
        assert pending_request() is None
    finally:
        restore()


def test_every_valid_action_is_accepted():
    restore = with_run_dir()
    try:
        for action in VALID_ACTIONS:
            request_action(action)
            assert pending_request() == action
    finally:
        restore()


def test_pending_request_is_none_before_anything_is_requested():
    restore = with_run_dir()
    try:
        assert pending_request() is None
    finally:
        restore()


def test_clear_request_removes_a_pending_request():
    restore = with_run_dir()
    try:
        request_action("restart")
        clear_request()
        assert pending_request() is None
        clear_request()  # Clearing twice is not an error.
    finally:
        restore()


def test_surrounding_whitespace_in_the_request_file_is_ignored():
    restore = with_run_dir()
    try:
        service_control.RUN_DIR.mkdir(parents=True, exist_ok=True)
        (service_control.RUN_DIR / "request").write_text("  restart \n")
        assert pending_request() == "restart"
    finally:
        restore()


def main():
    tests = [
        test_no_supervisor_when_pid_file_is_missing,
        test_supervised_when_pid_file_names_a_live_process,
        test_stale_pid_file_does_not_count_as_supervised,
        test_unreadable_pid_file_does_not_count_as_supervised,
        test_request_action_writes_the_action_for_the_supervisor,
        test_request_action_creates_the_run_directory,
        test_latest_request_replaces_the_previous_one,
        test_unknown_action_is_rejected,
        test_every_valid_action_is_accepted,
        test_pending_request_is_none_before_anything_is_requested,
        test_clear_request_removes_a_pending_request,
        test_surrounding_whitespace_in_the_request_file_is_ignored,
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
