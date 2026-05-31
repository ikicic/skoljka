from typing import Any, Protocol, cast

from django.db import models

from skoljka.apps.problems.models import Problem
from skoljka.apps.sources.models import Source, SourceDocument
from skoljka.utils.permissions import PermissionType


class UserLike(Protocol):
    is_authenticated: bool
    is_staff: bool


def source_year_problem_queryset(user: UserLike, source: Source, year: int) -> models.QuerySet[Problem]:
    source_ids = source_and_descendant_order(source, user)
    source_ordering = source_ordering_case(source_ids)
    return (
        _problem_queryset_for_user(user)
        .filter(source_id__in=source_ids, year=year)
        .order_by(
            source_ordering,
            models.F("problem_label").asc(nulls_last=True),
            "id",
        )
        .select_related("source")
        .prefetch_related("content__attachments")
    )


def source_problem_queryset(user: UserLike, source: Source) -> models.QuerySet[Problem]:
    source_ids = source_and_descendant_order(source, user)
    source_ordering = source_ordering_case(source_ids)
    return (
        _problem_queryset_for_user(user)
        .filter(source_id__in=source_ids)
        .order_by(
            source_ordering,
            models.F("year").desc(nulls_last=True),
            models.F("problem_label").asc(nulls_last=True),
            "id",
        )
        .select_related("source")
        .prefetch_related("content__attachments")
    )


def source_document_queryset(_user: UserLike, source: Source, year: int | None = None) -> models.QuerySet[SourceDocument]:
    # Source documents intentionally inherit visibility from the source page.
    # If documents need their own privacy later, this is the policy boundary.
    queryset = SourceDocument.objects.filter(source=source)
    if year is not None:
        queryset = queryset.filter(year=year)
    return queryset


def source_and_descendant_order(source: Source, user: UserLike) -> list[int]:
    sources = list(_source_queryset_for_user(user).only("id", "parent_id", "order", "slug"))
    by_parent: dict[int | None, list[Source]] = {}
    for item in sources:
        by_parent.setdefault(item.parent_id, []).append(item)
    for children in by_parent.values():
        children.sort(key=lambda item: (item.order, item.slug))

    result: list[int] = []
    seen: set[int] = set()

    def visit(source_id: int) -> None:
        seen.add(source_id)
        result.append(source_id)
        for child in by_parent.get(source_id, []):
            if child.id not in seen:
                visit(child.id)

    visit(source.id)
    return result


def source_ordering_case(source_ids: list[int]) -> models.Case:
    return models.Case(
        *[models.When(source_id=source_id, then=pos) for pos, source_id in enumerate(source_ids)],
        output_field=models.IntegerField(),
    )


def compact_source_year_title_context(problems: list[Problem], source: Source, year: int | None) -> tuple[int, int] | None:
    if year is None:
        return None
    source_ids = {problem.source_id for problem in problems}
    if source_ids == {source.pk}:
        return (source.pk, year)
    return None


def can_bulk_edit_problem_ids(user: UserLike | None, problem_ids: list[int]) -> bool:
    if not user or not user.is_authenticated or not problem_ids:
        return False
    editable_ids = set(
        _problem_queryset_for_user(user, "edit")
        .filter(pk__in=problem_ids)
        .values_list("pk", flat=True)
    )
    return editable_ids == set(problem_ids)


def _problem_queryset_for_user(user: UserLike, permission: PermissionType = "view") -> models.QuerySet[Problem]:
    manager = cast(Any, Problem.objects)
    return cast(models.QuerySet[Problem], manager.for_user(user, permission))


def _source_queryset_for_user(user: UserLike) -> models.QuerySet[Source]:
    manager = cast(Any, Source.objects)
    return cast(models.QuerySet[Source], manager.for_user(user))
