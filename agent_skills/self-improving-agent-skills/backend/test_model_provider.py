"""Tests provider selection between Gemini and Ollama Cloud.

The optimizer can run against either. Which one it picks is decided entirely by
what is configured in backend/.env, so these tests pin that precedence down.

    python test_model_provider.py
"""

import dataclasses
import os
import sys

from model_provider import (
    DEFAULT_OLLAMA_API_BASE,
    DEFAULT_OLLAMA_MODEL,
    GEMINI_KEY_NAME,
    OLLAMA_API_BASE_NAME,
    OLLAMA_KEY_NAME,
    OLLAMA_MODEL_NAME,
    describe_provider,
    resolve_provider,
)

GEMINI_KEY = "gemini-env-key"
OLLAMA_KEY = "ollama-env-key"
REQUEST_KEY = "key-pasted-in-the-ui"

MANAGED = (GEMINI_KEY_NAME, OLLAMA_KEY_NAME, OLLAMA_MODEL_NAME, OLLAMA_API_BASE_NAME)


def with_env(**values):
    """Sets the provider variables, returning a callable that restores them."""
    previous = {name: os.environ.get(name) for name in MANAGED}

    for name in MANAGED:
        os.environ.pop(name, None)
    for name, value in values.items():
        if value is not None:
            os.environ[name] = value

    def restore():
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    return restore


def test_no_configuration_means_no_provider():
    restore = with_env()
    try:
        assert resolve_provider(None) is None
        assert describe_provider() == {
            "has_env_key": False,
            "provider": None,
            "model": None,
        }
    finally:
        restore()


def test_gemini_key_alone_selects_gemini():
    restore = with_env(**{GEMINI_KEY_NAME: GEMINI_KEY})
    try:
        provider = resolve_provider(None)
        assert provider.name == "gemini", provider
        assert provider.api_key == GEMINI_KEY
        assert provider.api_base is None, "Gemini talks to Google, not a custom host"
    finally:
        restore()


def test_ollama_key_alone_selects_ollama_cloud():
    restore = with_env(**{OLLAMA_KEY_NAME: OLLAMA_KEY})
    try:
        provider = resolve_provider(None)
        assert provider.name == "ollama", provider
        assert provider.api_key == OLLAMA_KEY
        assert provider.model == DEFAULT_OLLAMA_MODEL
        assert provider.api_base == DEFAULT_OLLAMA_API_BASE
    finally:
        restore()


def test_ollama_wins_when_both_are_configured():
    """Adding an Ollama key is the explicit opt-in; it should take effect."""
    restore = with_env(
        **{GEMINI_KEY_NAME: GEMINI_KEY, OLLAMA_KEY_NAME: OLLAMA_KEY}
    )
    try:
        assert resolve_provider(None).name == "ollama"
    finally:
        restore()


def test_a_key_pasted_in_the_ui_is_a_gemini_key_and_wins():
    """The UI field predates Ollama support and still sends a Gemini key."""
    restore = with_env(**{OLLAMA_KEY_NAME: OLLAMA_KEY})
    try:
        provider = resolve_provider(REQUEST_KEY)
        assert provider.name == "gemini", provider
        assert provider.api_key == REQUEST_KEY
    finally:
        restore()


def test_blank_request_key_does_not_override_ollama():
    restore = with_env(**{OLLAMA_KEY_NAME: OLLAMA_KEY})
    try:
        for blank in ("", "   ", None):
            assert resolve_provider(blank).name == "ollama", blank
    finally:
        restore()


def test_ollama_model_and_host_can_be_overridden():
    restore = with_env(
        **{
            OLLAMA_KEY_NAME: OLLAMA_KEY,
            OLLAMA_MODEL_NAME: "kimi-k2.7-code",
            OLLAMA_API_BASE_NAME: "https://ollama.internal/v1",
        }
    )
    try:
        provider = resolve_provider(None)
        assert provider.model == "kimi-k2.7-code", provider
        assert provider.api_base == "https://ollama.internal/v1", provider
    finally:
        restore()


def test_blank_ollama_key_is_not_configuration():
    restore = with_env(**{OLLAMA_KEY_NAME: "   ", GEMINI_KEY_NAME: GEMINI_KEY})
    try:
        assert resolve_provider(None).name == "gemini"
    finally:
        restore()


def test_describe_provider_reports_the_active_model():
    restore = with_env(**{OLLAMA_KEY_NAME: OLLAMA_KEY})
    try:
        assert describe_provider() == {
            "has_env_key": True,
            "provider": "ollama",
            "model": DEFAULT_OLLAMA_MODEL,
        }
    finally:
        restore()


def test_provider_config_is_immutable():
    restore = with_env(**{GEMINI_KEY_NAME: GEMINI_KEY})
    try:
        provider = resolve_provider(None)
        try:
            provider.model = "something-else"
        except dataclasses.FrozenInstanceError:
            return
        raise AssertionError("ProviderConfig should be frozen")
    finally:
        restore()


def main():
    tests = [
        test_no_configuration_means_no_provider,
        test_gemini_key_alone_selects_gemini,
        test_ollama_key_alone_selects_ollama_cloud,
        test_ollama_wins_when_both_are_configured,
        test_a_key_pasted_in_the_ui_is_a_gemini_key_and_wins,
        test_blank_request_key_does_not_override_ollama,
        test_ollama_model_and_host_can_be_overridden,
        test_blank_ollama_key_is_not_configuration,
        test_describe_provider_reports_the_active_model,
        test_provider_config_is_immutable,
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
