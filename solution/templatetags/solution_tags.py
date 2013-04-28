from django import template
from django.utils.safestring import mark_safe

from skoljka.utils import interpolate_colors
from skoljka.utils.string_operations import obfuscate_text

from solution.models import Solution, STATUS, HTML_INFO

from datetime import datetime, timedelta

register = template.Library()

@register.simple_tag(takes_context=True)
def filter_solutions_by_status(context, solutions, filter_by_status):
    """
        Ukratko:
        problem je u tome sto useroptions update-a tek u renderu.
        zato ova funkcija dodaje potrebne filtere, ali pazi na slucaj kada se vec
        pretrazuje po odredjenom statusu (filter_by_status-u)
    """

    print 'FILTER_BY_STATUS', filter_by_status
    print 'SOLUTION_STATUS_FILTER', context['solution_status_filter']
    if filter_by_status is not None:
        status = filter_by_status
    else:
        status = context['solution_status_filter']
    status = status.split(',')

    print 'STATUS', status

    # pass by reference?
    if len(status) == 1:
        if status[0]:
            context['solutions'] = solutions.filter(status=STATUS[status[0]])
    else:
        context['solutions'] = solutions.filter(status__in=[STATUS[x] for x in status])
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
    percent = 1 if days < 3 else (.6 if days < 90 else .2)

    if row_number % 2 == 1:
        r, g, b = interpolate_colors(240, 245, 244, # #content.color
            r * 1.01, g * 1.01, b * 1.01, percent)
        r = min(r, 255)
        g = min(g, 255)
        b = min(b, 255)
    else:
        r, g, b = interpolate_colors(244, 247, 246, # .table-striped odd-child
            r, g, b, percent)

    return "background-color:#%02X%02X%02X;" % (r, g, b)

@register.simple_tag
def solution_label(task):
    # TODO: rename to _cache_solution
    cache = getattr(task, 'cache_solution', None)
    if not cache or cache.is_blank():
        return ''
    return u'<span class="label %(label_class)s">%(label_text)s</span>' % cache.get_html_info()

@register.simple_tag(takes_context=True)
def cache_solution_info(context, solutions):
    user = context['user']

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
def check_solution_for_obfuscation(context, solution, text):
    my_solution = getattr(solution, '_cache_my_solution', None)
    if solution.should_obfuscate(context['user'], my_solution):
        text = obfuscate_text(text)
        title = mark_safe(u'title="Niste riješili ovaj zadatak!"')
    else:
        title = u''

    context['obfuscation_text'] = text
    context['obfuscation_title'] = title

    return ''
