from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def cached_permission(group, type):
    if hasattr(group, '_cache_permissions'):
        if type in group._cache_permissions:
            return mark_safe('<i class="icon-ok"></i>')
        else:
            return ''
    else:
        return '??'
