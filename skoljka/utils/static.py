import os
from pathlib import Path

from django.conf import settings

_STATIC_DIR = Path(settings.STATICFILES_DIRS[0]) if settings.STATICFILES_DIRS else settings.BASE_DIR / "static"
_cache: dict[str, str] = {}


def _get_version(path: str) -> str:
    filepath = _STATIC_DIR / path
    try:
        return str(int(os.path.getmtime(filepath)))
    except OSError:
        return "0"


def static_url(path: str) -> str:
    """Return a static URL with a cache-busting query parameter based on file mtime.

    In production (DEBUG=False), the mtime is cached after the first lookup.
    In development (DEBUG=True), the mtime is checked on every call.
    """
    if settings.DEBUG:
        version = _get_version(path)
    else:
        version = _cache.get(path)
        if version is None:
            version = _get_version(path)
            _cache[path] = version
    return f"/static/{path}?v={version}"
