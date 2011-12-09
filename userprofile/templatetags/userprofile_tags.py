from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def userlink(user):
    return mark_safe(u'<a href="/profile/%d/">%s</a>' % (user.pk, user.username))
