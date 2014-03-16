from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def grouplink(group):
    return mark_safe(u'<a href="/usergroup/%d/">%s</a>' % (group.id, group.name))

@register.simple_tag(takes_context=True)
def group_class_attr(context, group):
    user = context['user']

    if group.data.hidden:
        cls = 'group_hidden'
    elif group.id in context['user_group_ids']:
        # TODO: create another css class
        cls = 'task-as-solved'
    else:
        cls = ''

    return mark_safe(' class="{}"'.format(cls) if cls else '')
