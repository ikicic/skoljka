from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def solution_label(task):
    cache = getattr(task, 'cache_solution', None)
    if not cache or cache.is_blank():
        return ''
    return u'<span class="label %(label_class)s">%(label_text)s</span>' % cache.get_html_info()
