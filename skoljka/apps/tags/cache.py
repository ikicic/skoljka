import time

from django.utils.translation import override

from skoljka.apps.tags.models import Tag

_version = str(time.time_ns())
_responses: dict[str, dict[str, list[str]]] = {}


def tag_api_version() -> str:
    return _version


def tag_api_url(language: str) -> str:
    return f"/tags/api/{language}/{tag_api_version()}.json"


def tag_api_data(language: str) -> dict[str, list[str]]:
    language = language.split("-")[0]
    cached = _responses.get(language)
    if cached is not None:
        return cached

    with override(language):
        tags = list(Tag.objects.filter(hidden=False).order_by("slug"))
        data = {
            "names": [t.display_name() for t in tags],
            "full_names": [t.name() for t in tags],
            "slugs": [t.slug for t in tags],
            "kinds": [t.kind for t in tags],
        }
    _responses[language] = data
    return data


def clear_tag_api_cache() -> None:
    global _version
    _version = str(time.time_ns())
    _responses.clear()
