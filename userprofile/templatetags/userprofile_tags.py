from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def userlink(user, what=None):
    name = None
    if what == 'full':
        name = user.get_full_name().strip()
    elif what:
        name = getattr(user, what, None)
        
    # full_name kao default bi stvarao gadne probleme kod PM-a
    if not name:
        name = user.username
            
    return mark_safe(u'<a href="/profile/%d/">%s</a>' % (user.pk, name))
