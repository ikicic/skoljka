"""Helpers for transcription provider credentials."""

import os


def require_api_key(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not configured.")
    return value
