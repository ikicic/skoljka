from django import template
from django.utils.safestring import mark_safe

from skoljka.utils import xss

register = template.Library()

@register.filter
def grouplink(group):
    return mark_safe(u'<a href="/usergroup/{}/">{}</a>'.format(
            group.id, xss.escape(group.name)))


@register.simple_tag(takes_context=True)
def group_class_attr(context, group):
    user = context['user']

    if group.data.hidden:
        cls = 'group-hidden'
    elif group.id in context['user_group_ids']:
        # TODO: create another css class
        cls = 'group-is-member-of'
    else:
        cls = ''

    return mark_safe(' class="{}"'.format(cls) if cls else '')
