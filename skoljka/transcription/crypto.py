"""Encryption helpers for transcription jobs and API cache entries."""

import base64
import gzip
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

_FILE_INFO = b"skoljka-transcription-files-v1"
_CACHE_INFO = b"skoljka-transcription-cache-v1"


def _derive(material: bytes, info: bytes) -> bytes:
    raw = HKDF(algorithm=SHA256(), length=32, salt=None, info=info).derive(material)
    return base64.urlsafe_b64encode(raw)


def file_key() -> bytes:
    """Fernet-ready key derived only from SECRET_KEY."""
    return _derive(settings.SECRET_KEY.encode(), _FILE_INFO)


def cache_key() -> bytes:
    """Fernet-ready key derived from SECRET_KEY and transcription API keys."""
    parts = [
        settings.SECRET_KEY.encode(),
        os.environ.get("MISTRAL_API_KEY", "").encode(),
        os.environ.get("ANTHROPIC_API_KEY", "").encode(),
    ]
    return _derive(b"\x00".join(parts), _CACHE_INFO)


def encrypt_blob(data: bytes, key: bytes) -> bytes:
    return Fernet(key).encrypt(gzip.compress(data, compresslevel=6))


def decrypt_blob(blob: bytes, key: bytes) -> bytes:
    return gzip.decompress(Fernet(key).decrypt(blob))
