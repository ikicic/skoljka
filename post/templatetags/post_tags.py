from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.inclusion_tag('inc_post_list_small.html', takes_context=True)
def show_posts_small(context, container):
    return {
        'container': container,
        'request': context['request'],
        'user': context['user'],
    }
