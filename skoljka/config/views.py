import hashlib
from pathlib import Path

from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect
from django.utils.translation import override
from django.views.i18n import JavaScriptCatalog

from skoljka.utils.cache_headers import set_immutable_cache

_javascript_catalog_version: str | None = None


def javascript_catalog_url(language: str) -> str:
    return f"/jsi18n/{language}/{javascript_catalog_version()}.js"


def javascript_catalog_version() -> str:
    global _javascript_catalog_version
    if _javascript_catalog_version is not None and not settings.DEBUG:
        return _javascript_catalog_version

    paths = [
        Path(__file__),
        settings.BASE_DIR / "static" / "ts" / "i18n-messages.ts",
    ]
    paths.extend((settings.BASE_DIR / "locale").glob("**/*.mo"))

    digest = hashlib.sha256()
    for path in sorted(paths):
        try:
            content = path.read_bytes()
        except OSError:
            continue
        digest.update(str(path.relative_to(settings.BASE_DIR)).encode())
        digest.update(b"\0")
        digest.update(content)
    version = digest.hexdigest()[:12]
    if not settings.DEBUG:
        _javascript_catalog_version = version
    return version


def versioned_javascript_catalog(request: HttpRequest, language: str, version: str):
    current_version = javascript_catalog_version()
    if version != current_version:
        response = HttpResponseRedirect(javascript_catalog_url(language))
        response["Cache-Control"] = "no-store"
        return response
    with override(language):
        response = JavaScriptCatalog.as_view()(request)
    return set_immutable_cache(response)
