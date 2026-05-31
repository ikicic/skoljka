from typing import Any, Protocol, cast

from django.db.models import Case, Count, IntegerField, Q, When

from skoljka.apps.lists.models import ProblemList, ProblemListItem
from skoljka.apps.problems.models import Problem
from skoljka.apps.tracking.models import Submission
from skoljka.utils.permissions import PermissionType


class UserLike(Protocol):
    is_authenticated: bool
    is_staff: bool


def visible_problem_counts(lists: list[ProblemList], user: UserLike) -> dict[int, int]:
    if not lists:
        return {}
    list_ids = {pl.pk for pl in lists}
    visible_problem_ids = _problem_queryset_for_user(user).values("id")
    return dict(
        ProblemListItem.objects
        .filter(
            problem_list_id__in=list_ids,
            problem_id__in=visible_problem_ids,
        )
        .values("problem_list_id")
        .annotate(count=Count("id"))
        .values_list("problem_list_id", "count")
    )


def visible_solved_problem_counts(lists: list[ProblemList], user: UserLike) -> dict[int, int]:
    if not lists or not user.is_authenticated:
        return {}
    list_ids = {pl.pk for pl in lists}
    visible_problem_ids = _problem_queryset_for_user(user).values("id")
    return dict(
        ProblemListItem.objects
        .filter(
            problem_list_id__in=list_ids,
            problem_id__in=visible_problem_ids,
        )
        .values("problem_list_id")
        .annotate(
            count=Count(
                "problem_id",
                filter=Q(problem__submissions__user=user, problem__submissions__solved=True),
                distinct=True,
            )
        )
        .values_list("problem_list_id", "count")
    )


def ordered_list_problem_queryset(problem_list: ProblemList, user: UserLike):
    problem_ids = list(
        ProblemListItem.objects
        .filter(problem_list=problem_list)
        .order_by("order", "id")
        .values_list("problem_id", flat=True)
    )
    if not problem_ids:
        return Problem.objects.none()
    ordering = Case(
        *[When(pk=problem_id, then=pos) for pos, problem_id in enumerate(problem_ids)],
        output_field=IntegerField(),
    )
    return _problem_queryset_for_user(user).filter(id__in=problem_ids).order_by(ordering)


def solved_problem_ids(problems: list[Problem], user: UserLike | None) -> set[int]:
    if not user or not user.is_authenticated or not problems:
        return set()
    return set(
        Submission.objects.filter(
            user=user,
            problem_id__in=[problem.pk for problem in problems],
            solved=True,
        ).values_list("problem_id", flat=True)
    )


def _problem_queryset_for_user(user: UserLike, permission: PermissionType = "view"):
    manager = cast(Any, Problem.objects)
    return manager.for_user(user, permission)
