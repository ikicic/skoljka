"""Shared test helpers for constructing model instances."""

from itertools import count

from skoljka.apps.accounts.models import User
from skoljka.apps.content.models import Content
from skoljka.apps.lists.models import ProblemList, ProblemListItem
from skoljka.apps.problems.models import Problem
from skoljka.apps.sources.models import Source
from skoljka.apps.tags.models import Tag

_counter = count(1)


def _next() -> int:
    return next(_counter)


def make_user(
    username: str | None = None,
    email: str | None = None,
    password: str = "correct-horse-battery-staple",
    *,
    is_staff: bool = False,
    **extra,
) -> User:
    n = _next()
    username = username or f"user{n}"
    email = email or f"{username}@example.test"
    user = User.objects.create_user(
        username=username, email=email, password=password, **extra
    )
    if is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    return user


def make_staff(**kwargs) -> User:
    return make_user(is_staff=True, **kwargs)


def make_source(
    slug: str | None = None,
    name: str = "Test Source",
    *,
    parent: Source | None = None,
    is_public: bool = True,
    created_by: User | None = None,
    translations: dict | None = None,
) -> Source:
    n = _next()
    slug = slug or f"src-{n}"
    translations = translations or {"en": {"name": name}}
    return Source.objects.create(
        slug=slug,
        parent=parent,
        translations=translations,
        is_public=is_public,
        created_by=created_by,
    )


def make_tag(
    slug: str | None = None,
    name: str = "Tag",
    *,
    kind: str = Tag.Kind.TOPIC,
    parent: Tag | None = None,
    hidden: bool = False,
    translations: dict | None = None,
    short_translations: dict | None = None,
    descriptions: dict | None = None,
) -> Tag:
    n = _next()
    slug = slug or f"tag-{n}"
    translations = translations if translations is not None else {"en": name}
    return Tag.objects.create(
        slug=slug,
        kind=kind,
        parent=parent,
        hidden=hidden,
        translations=translations,
        short_translations=short_translations or {},
        descriptions=descriptions or {},
    )


def make_problem(
    *,
    title: str = "",
    source: Source | None = None,
    year: int | None = None,
    problem_label: int | str | None = None,
    is_public: bool = True,
    created_by: User | None = None,
    content: str | None = None,
    language: str = "en",
) -> Problem:
    problem = Problem.objects.create(
        title=title,
        source=source,
        year=year,
        problem_label="" if problem_label is None else str(problem_label),
        is_public=is_public,
        created_by=created_by,
    )
    if content is not None:
        make_content(problem, source_md=content, language=language)
    return problem


def make_content(
    obj,
    source_md: str = "Problem statement.",
    language: str = "en",
) -> Content:
    return Content.objects.create(
        content_object=obj,
        original_language=language,
        source_md={language: source_md},
    )


def make_list(
    title: str = "My list",
    *,
    created_by: User | None = None,
    is_public: bool = True,
    description: str = "",
) -> ProblemList:
    return ProblemList.objects.create(
        title=title,
        description=description,
        is_public=is_public,
        created_by=created_by,
    )


def add_to_list(pl: ProblemList, problem: Problem, order: int = 0) -> ProblemListItem:
    return ProblemListItem.objects.create(
        problem_list=pl, problem=problem, order=order
    )
