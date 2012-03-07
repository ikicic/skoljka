from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def userlink(user, what=None):
    name = None
    if what:
        name = getattr(user, what, None)
        
    if not name:
        if user.first_name and user.last_name:
            name = '%s %s' % (user.first_name, user.last_name)
        else:
            name = user.username
            
    return mark_safe(u'<a href="/profile/%d/">%s</a>' % (user.pk, name))
