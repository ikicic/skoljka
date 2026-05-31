from django.utils.text import slugify

from skoljka.apps.tags.models import Tag


def _split_values(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return result


def resolve_tags(slugs: list[str], new_names: list[str] | None = None) -> list[Tag]:
    slugs = _split_values(slugs)
    new_names = _split_values(new_names or [])
    tags = list(Tag.objects.filter(slug__in=slugs))
    by_slug = {tag.slug: tag for tag in tags}

    for name in new_names:
        name = name.strip()
        slug = slugify(name)
        if not name or not slug:
            continue
        if slug in by_slug:
            continue
        tag, _created = Tag.objects.get_or_create(
            slug=slug,
            defaults={
                "kind": Tag.Kind.TOPIC,
                "translations": {"en": name},
            },
        )
        by_slug[tag.slug] = tag

    return list(by_slug.values())
