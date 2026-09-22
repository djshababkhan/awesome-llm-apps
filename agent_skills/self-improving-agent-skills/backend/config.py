"""Resolves the Gemini API key from the environment or the incoming request.

The key is read from backend/.env so it only has to be entered once. A key sent
in a request still wins, which keeps the paste-a-key flow working for anyone who
has not created a .env file.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ENV_KEY_NAME = "GOOGLE_API_KEY"
ENV_FILE = Path(__file__).parent / ".env"


def load_env_file() -> None:
    """Loads backend/.env if present. Existing environment variables win."""
    load_dotenv(ENV_FILE, override=False)


def clean_value(value: Optional[str]) -> Optional[str]:
    """Normalizes a setting, treating blank or whitespace-only values as absent."""
    if not value:
        return None
    stripped = value.strip()
    return stripped or None


def has_env_key() -> bool:
    """Whether a usable key is configured in the environment."""
    return clean_value(os.environ.get(ENV_KEY_NAME)) is not None


def resolve_api_key(request_key: Optional[str]) -> Optional[str]:
    """The key to use for a request, or None when none is configured anywhere."""
    return clean_value(request_key) or clean_value(os.environ.get(ENV_KEY_NAME))
