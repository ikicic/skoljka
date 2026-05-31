import random

from django.core.cache import cache
from django.db.models import Case, IntegerField, Q, When

from skoljka.apps.problems.models import Problem

HOME_PUBLIC_PROBLEM_IDS_KEY = "home:public_problem_ids"
HOME_PUBLIC_PROBLEM_IDS_TTL = 3600


def public_home_problem_queryset(user):
    return (
        Problem.objects.for_user(user)
        .filter(is_public=True)
        .filter(Q(source__isnull=True) | Q(source__is_public=True))
    )


def _query_public_home_problem_ids() -> list[int]:
    return list(
        Problem.objects.filter(is_public=True)
        .filter(Q(source__isnull=True) | Q(source__is_public=True))
        .order_by("id")
        .values_list("pk", flat=True)
    )


def cached_public_home_problem_ids() -> list[int]:
    """IDs of problems eligible for the homepage random section.

    The homepage only shows public problems from public sources, so this pool
    is shared across users. Refresh it periodically instead of scanning the table
    on every request.
    """
    ids = cache.get(HOME_PUBLIC_PROBLEM_IDS_KEY)
    if ids:
        existing = set(_query_public_home_problem_ids())
        valid = [problem_id for problem_id in ids if problem_id in existing]
        if valid:
            return valid
        cache.delete(HOME_PUBLIC_PROBLEM_IDS_KEY)
    ids = _query_public_home_problem_ids()
    if ids:
        cache.set(HOME_PUBLIC_PROBLEM_IDS_KEY, ids, HOME_PUBLIC_PROBLEM_IDS_TTL)
    return ids


def invalidate_public_home_problem_ids() -> None:
    cache.delete(HOME_PUBLIC_PROBLEM_IDS_KEY)


def random_public_home_problems(*, exclude_ids: list[int], limit: int) -> list[Problem]:
    from skoljka.apps.problems.components import problems_table_queryset

    pool = [problem_id for problem_id in cached_public_home_problem_ids() if problem_id not in exclude_ids]
    if not pool or limit <= 0:
        return []
    sample_ids = random.sample(pool, min(limit, len(pool)))
    ordering = Case(
        *[When(pk=problem_id, then=pos) for pos, problem_id in enumerate(sample_ids)],
        output_field=IntegerField(),
    )
    return list(
        problems_table_queryset(Problem.objects.filter(pk__in=sample_ids).order_by(ordering))
    )
