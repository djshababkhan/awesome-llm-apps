"""Tests for API key resolution between .env and the request body.

    python test_config.py
"""

import os
import sys

from config import ENV_KEY_NAME, has_env_key, resolve_api_key

REQUEST_KEY = "key-from-request"
ENV_VALUE = "key-from-env"


def with_env(value):
    """Sets or clears the environment key, returning a restore callable."""
    previous = os.environ.get(ENV_KEY_NAME)

    if value is None:
        os.environ.pop(ENV_KEY_NAME, None)
    else:
        os.environ[ENV_KEY_NAME] = value

    def restore():
        if previous is None:
            os.environ.pop(ENV_KEY_NAME, None)
        else:
            os.environ[ENV_KEY_NAME] = previous

    return restore


def test_uses_env_key_when_request_omits_one():
    restore = with_env(ENV_VALUE)
    try:
        assert resolve_api_key("") == ENV_VALUE
        assert resolve_api_key(None) == ENV_VALUE
    finally:
        restore()


def test_request_key_overrides_env():
    restore = with_env(ENV_VALUE)
    try:
        assert resolve_api_key(REQUEST_KEY) == REQUEST_KEY
    finally:
        restore()


def test_returns_none_when_no_key_anywhere():
    restore = with_env(None)
    try:
        assert resolve_api_key("") is None
        assert resolve_api_key(None) is None
    finally:
        restore()


def test_whitespace_only_key_is_not_a_key():
    restore = with_env(None)
    try:
        assert resolve_api_key("   ") is None
    finally:
        restore()


def test_surrounding_whitespace_is_stripped():
    restore = with_env(None)
    try:
        assert resolve_api_key(f"  {REQUEST_KEY}  ") == REQUEST_KEY
    finally:
        restore()


def test_has_env_key_reflects_environment():
    restore = with_env(ENV_VALUE)
    try:
        assert has_env_key() is True
    finally:
        restore()

    restore = with_env(None)
    try:
        assert has_env_key() is False
    finally:
        restore()


def test_blank_env_key_does_not_count_as_configured():
    restore = with_env("   ")
    try:
        assert has_env_key() is False
        assert resolve_api_key("") is None
    finally:
        restore()


def main():
    tests = [
        test_uses_env_key_when_request_omits_one,
        test_request_key_overrides_env,
        test_returns_none_when_no_key_anywhere,
        test_whitespace_only_key_is_not_a_key,
        test_surrounding_whitespace_is_stripped,
        test_has_env_key_reflects_environment,
        test_blank_env_key_does_not_count_as_configured,
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
