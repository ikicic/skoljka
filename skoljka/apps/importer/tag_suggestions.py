"""LLM-assisted topic tag suggestions for problem import drafts."""

import hashlib
import json
import logging
from typing import Any

from django.db.models import QuerySet

from skoljka.apps.tags.models import Tag
from skoljka.transcription.cache import APICache
from skoljka.transcription.chat import ChatProvider, make_chat_provider, parse_model_flag

logger = logging.getLogger(__name__)

MAX_PROBLEMS_PER_REQUEST = 30
MAX_CHARS_PER_PROBLEM = 4000
MAX_TAGS_PER_PROBLEM = 5

SUGGESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["index", "tags"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["suggestions"],
    "additionalProperties": False,
}


def suggest_tags_for_sources(
    source_md_list: list[str],
    *,
    model: str,
    cache: APICache,
    chat_provider: ChatProvider | None = None,
    tags_queryset: QuerySet[Tag] | None = None,
) -> list[list[str]]:
    """Return suggested topic tag slugs aligned with source_md_list."""
    if not source_md_list:
        return []
    tags = _tag_payload(tags_queryset)
    if not tags:
        return [[] for _ in source_md_list]

    provider_name, model_name = parse_model_flag(model)
    chat_provider = chat_provider or make_chat_provider(provider_name)
    allowed_slugs = {tag["slug"] for tag in tags}
    result: list[list[str]] = [[] for _ in source_md_list]

    for offset in range(0, len(source_md_list), MAX_PROBLEMS_PER_REQUEST):
        chunk = source_md_list[offset:offset + MAX_PROBLEMS_PER_REQUEST]
        suggestions = _suggest_chunk(
            chunk,
            offset=offset,
            tags=tags,
            allowed_slugs=allowed_slugs,
            model=model_name,
            cache_model=model,
            cache=cache,
            chat_provider=chat_provider,
        )
        for index, slugs in suggestions.items():
            if 0 <= index < len(result):
                result[index] = slugs

    return result


def _tag_payload(tags_queryset: QuerySet[Tag] | None = None) -> list[dict[str, str]]:
    queryset = tags_queryset if tags_queryset is not None else Tag.objects.filter(kind=Tag.Kind.TOPIC, hidden=False)
    tags = []
    for tag in queryset.order_by("slug"):
        description = tag.descriptions.get("en") or tag.name("en")
        tags.append({"slug": tag.slug, "description": description})
    return tags


def _suggest_chunk(
    source_md_list: list[str],
    *,
    offset: int,
    tags: list[dict[str, str]],
    allowed_slugs: set[str],
    model: str,
    cache_model: str,
    cache: APICache,
    chat_provider: ChatProvider,
) -> dict[int, list[str]]:
    system = _system_prompt(tags)
    content = _user_prompt(source_md_list, offset)
    cache_key = _cache_key(system, content, cache_model)
    cached = cache.get(cache_key)
    if cached is not None:
        raw = json.loads(cached)
    else:
        logger.info(
            "Sending tag suggestion request to %s (%d problems, %d tags)",
            cache_model,
            len(source_md_list),
            len(tags),
        )
        raw = chat_provider.structured_chat(system, content, model, SUGGESTION_SCHEMA)
        cache.put(cache_key, json.dumps(raw, separators=(",", ":"), sort_keys=True))
    return _validate_suggestions(raw, offset, len(source_md_list), allowed_slugs)


def _system_prompt(tags: list[dict[str, str]]) -> str:
    return (
        "You assign topic tags to math competition problems.\n\n"
        "Allowed tags are listed below as JSON objects with slug and description. "
        "Use only these slugs.\n\n"
        f"{json.dumps(tags, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "Rules:\n"
        "- Suggest only topic tags from the allowed list.\n"
        f"- Suggest 0 to {MAX_TAGS_PER_PROBLEM} tags per problem.\n"
        "- Prefer broad, clearly applicable tags.\n"
        "- Always try to include one broad area tag when applicable: "
        "algebra, combinatorics, geometry, or number-theory.\n"
        "- Do not infer solution techniques.\n"
        "- If unsure, return fewer tags.\n"
        "- Return suggestions keyed by the provided draft index."
    )


def _user_prompt(source_md_list: list[str], offset: int) -> str:
    problems = [
        {
            "index": offset + i,
            "statement": source[:MAX_CHARS_PER_PROBLEM],
        }
        for i, source in enumerate(source_md_list)
    ]
    return json.dumps({"problems": problems}, ensure_ascii=False)


def _cache_key(system: str, content: str, model: str) -> str:
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(system.encode())
    h.update(content.encode())
    h.update(json.dumps(SUGGESTION_SCHEMA, sort_keys=True).encode())
    return f"tag-suggestions:{h.hexdigest()}"


def _validate_suggestions(
    raw: dict,
    offset: int,
    count: int,
    allowed_slugs: set[str],
) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    suggestions = raw.get("suggestions", [])
    if not isinstance(suggestions, list):
        return result

    valid_indices = set(range(offset, offset + count))
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        if not isinstance(index, int) or index not in valid_indices:
            continue
        tags = item.get("tags", [])
        if not isinstance(tags, list):
            continue
        slugs = []
        seen = set()
        for slug in tags:
            if not isinstance(slug, str) or slug not in allowed_slugs or slug in seen:
                continue
            seen.add(slug)
            slugs.append(slug)
            if len(slugs) >= MAX_TAGS_PER_PROBLEM:
                break
        result[index] = slugs
    return result
