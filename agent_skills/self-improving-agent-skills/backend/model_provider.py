"""Chooses which model provider the optimizer runs against.

The loop makes a lot of sequential calls, so the model matters for both speed
and quality. Gemini remains the default, and setting OLLAMA_API_KEY in
backend/.env switches every agent over to a model hosted on Ollama Cloud
through its OpenAI-compatible endpoint. Nothing else in the app has to know
which one is in use.
"""

import os
from dataclasses import dataclass
from typing import Optional

from config import ENV_KEY_NAME as GEMINI_KEY_NAME
from config import clean_value

OLLAMA_KEY_NAME = "OLLAMA_API_KEY"
OLLAMA_MODEL_NAME = "OLLAMA_MODEL"
OLLAMA_API_BASE_NAME = "OLLAMA_API_BASE"

DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
DEFAULT_OLLAMA_MODEL = "kimi-k3"
DEFAULT_OLLAMA_API_BASE = "https://ollama.com/v1"

GEMINI = "gemini"
OLLAMA = "ollama"


@dataclass(frozen=True)
class ProviderConfig:
    """Everything the optimizer needs to build its agents' model."""

    name: str
    model: str
    api_key: str
    # Only set for OpenAI-compatible hosts; Gemini talks to Google directly.
    api_base: Optional[str] = None

    @property
    def enforces_response_schema(self) -> bool:
        """Whether the endpoint actually honours a requested output schema.

        Gemini does. Ollama Cloud accepts an OpenAI response_format and then
        answers in prose anyway, so callers there have to ask for JSON in the
        prompt the model reads.
        """
        return self.name == GEMINI


def _env(name: str) -> Optional[str]:
    return clean_value(os.environ.get(name))


def _ollama() -> Optional[ProviderConfig]:
    key = _env(OLLAMA_KEY_NAME)
    if key is None:
        return None
    return ProviderConfig(
        name=OLLAMA,
        model=_env(OLLAMA_MODEL_NAME) or DEFAULT_OLLAMA_MODEL,
        api_key=key,
        api_base=_env(OLLAMA_API_BASE_NAME) or DEFAULT_OLLAMA_API_BASE,
    )


def _gemini(api_key: str) -> ProviderConfig:
    return ProviderConfig(name=GEMINI, model=DEFAULT_GEMINI_MODEL, api_key=api_key)


def resolve_provider(request_key: Optional[str] = None) -> Optional[ProviderConfig]:
    """The provider to use for a request, or None when nothing is configured.

    A key pasted into the UI wins, because that field sends a Gemini key and
    someone typing one in means to use it. Otherwise an Ollama key wins over a
    Gemini one: adding it to .env is the deliberate opt-in.
    """
    pasted = clean_value(request_key)
    if pasted is not None:
        return _gemini(pasted)

    ollama = _ollama()
    if ollama is not None:
        return ollama

    gemini_key = _env(GEMINI_KEY_NAME)
    return _gemini(gemini_key) if gemini_key else None


def describe_provider() -> dict:
    """What the UI needs to know: whether it must ask for a key, and what runs."""
    provider = resolve_provider(None)
    if provider is None:
        return {"has_env_key": False, "provider": None, "model": None}
    return {
        "has_env_key": True,
        "provider": provider.name,
        "model": provider.model,
    }
