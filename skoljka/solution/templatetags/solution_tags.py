from datetime import datetime

from django import template
from django.utils.safestring import mark_safe

from skoljka.permissions.constants import VIEW_SOLUTIONS
from skoljka.permissions.utils import get_object_ids_with_exclusive_permission
from skoljka.solution.models import (
    HTML_INFO,
    SOLUTION_STATUS_BY_NAME,
    Solution,
    SolutionDetailedStatus,
)
from skoljka.task.models import Task
from skoljka.task.utils import check_prerequisites_for_tasks
from skoljka.utils import interpolate_colors
from skoljka.utils.string_operations import obfuscate_text

register = template.Library()


@register.simple_tag(takes_context=True)
def filter_solutions_by_status(context, solutions, filter_by_status):
    """
    Ukratko:
    problem je u tome sto useroptions update-a tek u renderu.
    zato ova funkcija dodaje potrebne filtere, ali pazi na slucaj kada se vec
    pretrazuje po odredjenom statusu (filter_by_status-u)
    """

    status = filter_by_status or context.get('solution_status_filter')
    if not status:
        return ''

    # temporary... hack.
    if status == 'unrated':
        context['solutions'] = solutions.filter(
            detailed_status=SolutionDetailedStatus.SUBMITTED_NOT_RATED
        )
        return ''

    context['solutions'] = solutions.filter(
        status__in=[SOLUTION_STATUS_BY_NAME.get(x, 0) for x in status.split(',')]
    )
    return ''


@register.simple_tag()
def solution_tr_bg_color_attr(solution, row_number):
    """
    Returns background-color (for style attribute) for given solution.
    """
    rgb = HTML_INFO[solution.detailed_status]['sol_rgb']
    if not rgb:
        return ''

    r, g, b = rgb

    days = (datetime.now() - solution.date_created).days
    percent = 0.5 if days < 3 else (0.25 if days < 90 else 0.15)

    if row_number % 2 == 1:
        r, g, b = interpolate_colors(
            240, 245, 244, r * 1.01, g * 1.01, b * 1.01, percent  # #content.color
        )
        r = min(r, 255)
        g = min(g, 255)
        b = min(b, 255)
    else:
        r, g, b = interpolate_colors(
            244, 247, 246, r, g, b, percent  # .table-striped odd-child
        )

    return "background-color:#%02X%02X%02X;" % (r, g, b)


@register.simple_tag
def solution_label(task):
    # TODO: rename to _cache_solution
    cache = getattr(task, 'cache_solution', None)
    if not cache or cache.is_blank():
        return ''
    return (
        u'<span class="label %(label_class)s">%(label_text)s</span>'
        % cache.get_html_info()
    )


@register.simple_tag(takes_context=True, name='cache_solution_info')
def _cache_solution_info(context, solutions):
    return cache_solution_info(context['user'], solutions)


def cache_solution_info(user, solutions):
    task_ids = [x.task_id for x in solutions]
    tasks = [x.task for x in solutions]
    check_prerequisites_for_tasks(tasks, user)

    if user.is_authenticated():
        my_solutions = Solution.objects.filter(author=user, task_id__in=task_ids)
        my_solutions = {x.task_id: x for x in my_solutions}
    else:
        my_solutions = {}

    # Can view solutions?
    # First, ignore those with SOLUTIONS_VISIBLE setting, and remove duplicates.
    explicit_ids = set(
        [
            x.task_id
            for x in solutions
            if x.task.solution_settings != Task.SOLUTIONS_VISIBLE
            and x.task.author_id != user.id
        ]
    )
    if explicit_ids:
        # Second, if any left, ask for permissions.
        explicit_ids = get_object_ids_with_exclusive_permission(
            user, VIEW_SOLUTIONS, model=Task, filter_ids=explicit_ids
        )
    explicit_ids = set(explicit_ids)

    for y in solutions:
        y._cache_my_solution = my_solutions.get(y.task_id)
        y.task._cache_can_view_solutions = (
            y.task_id in explicit_ids
            or y.task.solution_settings == Task.SOLUTIONS_VISIBLE
            or y.task.author_id == user.id
        )

    return ''


@register.simple_tag(takes_context=True)
def check_solution_for_accessibility(context, solution, text):
    my_solution = getattr(solution, '_cache_my_solution', None)
    can_view, should_obfuscate = solution.check_accessibility(
        context['user'], my_solution
    )

    if should_obfuscate:
        text = obfuscate_text(text)
        title = mark_safe(u'title="Niste riješili ovaj zadatak!"')
    else:
        title = u''

    if not can_view:
        if solution.task.solution_settings == Task.SOLUTIONS_NOT_VISIBLE:
            context['no_access_explanation'] = u'Rješenje nedostupno'
        else:  # Task.SOLUTIONS_VISIBLE_IF_ACCEPTED
            context[
                'no_access_explanation'
            ] = u'Rješenje dostupno samo korisnicima s točnim vlastitim rješenjem'

    context['can_view_solution'] = can_view
    context['obfuscation_text'] = text
    context['obfuscation_title'] = title

    return ''
