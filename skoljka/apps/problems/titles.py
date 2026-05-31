from django.utils.translation import gettext as _

from skoljka.apps.problems.models import Problem


def problem_title_context(problems: list[Problem], source_year: tuple[int, int] | None):
    if not source_year or not problems:
        return None
    source_id, year = source_year
    if any(p.title or p.source_id != source_id or p.year != year or not p.problem_label for p in problems):
        return None
    return source_year


def problem_display_title(problem: Problem, title_context=None) -> str:
    if title_context and problem.problem_label:
        return _("Problem %(number)s") % {"number": problem.problem_label}
    return problem.display_title
