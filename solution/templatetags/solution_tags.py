from django import template
from django.utils.safestring import mark_safe

from solution.models import STATUS

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
