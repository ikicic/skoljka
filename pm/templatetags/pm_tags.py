from django import template
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User, Group

from userprofile.templatetags.userprofile_tags import userlink

register = template.Library()

@register.filter
def recipientlink(r):
    if isinstance(r, User):
        return userlink(r)
    elif isinstance(r, Group):
        return r.data
    else:
        return r
