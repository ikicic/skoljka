from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from permissions import constants

register = template.Library()

@register.filter
def cached_permission(group, type):
    type = type.upper()
    if hasattr(constants, type):
        if hasattr(group, '_cache_permissions'):
            if getattr(constants, type) in group._cache_permissions:
                return mark_safe('<i class="icon-ok"></i>')
            else:
                return ''
        else:
            return '??'
    else:
        return 'Unknown permission type'
