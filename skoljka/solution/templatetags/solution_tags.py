from datetime import datetime

from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from skoljka.solution.models import (
    HTML_INFO,
    SOLUTION_STATUS_BY_NAME,
    Solution,
    SolutionDetailedStatus,
)
from skoljka.utils import interpolate_colors, xss
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

    if user.is_authenticated():
        my_solutions = Solution.objects.filter(author=user, task_id__in=task_ids)
        my_solutions = {x.task_id: x for x in my_solutions}
    else:
        my_solutions = {}

    for y in solutions:
        y._cache_my_solution = my_solutions.get(y.task_id)

    return ''


@register.simple_tag(takes_context=True)
def check_solution_for_accessibility(context, solution, text):
    my_solution = getattr(solution, '_cache_my_solution', None)
    if solution.should_obfuscate(context['user'], my_solution):
        text = obfuscate_text(text)
        title = mark_safe(
            u'title="%s"' % xss.escape(_("You haven't solved this problem!"))
        )
    else:
        title = u''

    context['obfuscation_text'] = text
    context['obfuscation_title'] = title

    return ''
