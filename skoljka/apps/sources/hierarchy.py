from skoljka.apps.sources.models import Source


def ordered_sources_with_depth(sources: list[Source]) -> list[tuple[Source, int]]:
    """Return sources in parent-before-children order.

    The input may contain a partial tree. If a source's parent is missing from
    the input, that source is treated as a root. Siblings are ordered by
    ``(order, slug)`` regardless of the input queryset ordering.
    """
    visible_ids = {source.id for source in sources}
    children_by_parent: dict[int | None, list[Source]] = {}
    for source in sources:
        parent_id = source.parent_id if source.parent_id in visible_ids else None
        children_by_parent.setdefault(parent_id, []).append(source)

    for children in children_by_parent.values():
        children.sort(key=lambda source: (source.order, source.slug))

    ordered: list[tuple[Source, int]] = []
    seen: set[int] = set()

    def visit(items: list[Source], depth: int) -> None:
        for source in items:
            if source.id in seen:
                continue
            seen.add(source.id)
            ordered.append((source, depth))
            visit(children_by_parent.get(source.id, []), depth + 1)

    visit(children_by_parent.get(None, []), 0)
    remaining = [source for source in sources if source.id not in seen]
    remaining.sort(key=lambda source: (source.order, source.slug))
    visit(remaining, 0)
    return ordered


def source_options_with_hierarchy_labels(
    sources: list[Source],
    *,
    indent: str = "-- ",
) -> list[tuple[Source, str]]:
    return [
        (source, f"{indent * depth}{source.name()}")
        for source, depth in ordered_sources_with_depth(sources)
    ]


def source_option_payload(source: Source, depth: int = 0) -> dict:
    return {
        "id": source.pk,
        "slug": source.slug,
        "name": source.name(),
        "parentId": source.parent_id,
        "order": source.order,
        "depth": depth,
    }


def source_options_payload(sources: list[Source]) -> list[dict]:
    return [
        source_option_payload(source, depth)
        for source, depth in ordered_sources_with_depth(sources)
    ]
