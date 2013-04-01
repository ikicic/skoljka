from django import template
from django.utils.safestring import mark_safe

from skoljka.utils.string_operations import obfuscate_text

from solution.models import Solution, STATUS

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

@register.simple_tag
def solution_label(task):
    cache = getattr(task, 'cache_solution', None)
    if not cache or cache.is_blank():
        return ''
    return u'<span class="label %(label_class)s">%(label_text)s</span>' % cache.get_html_info()

@register.simple_tag(takes_context=True)
def cache_solution_info(context, solutions):
    user = context['user']

    task_ids = [x.task_id for x in solutions]
    my_solutions = Solution.objects.filter(author=user, task_id__in=task_ids)
    my_solutions = {x.task_id: x for x in my_solutions}

    for y in solutions:
        y._cache_my_solution = my_solutions.get(y.task_id)

@register.simple_tag(takes_context=True)
def check_solution_for_obfuscation(context, solution, text):
    my_solution = getattr(solution, '_cache_my_solution', None)
    if solution.should_obfuscate(context['user'], my_solution):
        text = obfuscate_text(text)
        title = u'title="Niste riješili ovaj zadatak!"'
    else:
        title = u''

    context['obfuscation_text'] = text
    context['obfuscation_title'] = title

    return ''
