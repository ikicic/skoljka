from django import template
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User, Group

from userprofile.templatetags.userprofile_tags import userlink

from pm.models import MessageRecipient

from collections import defaultdict


register = template.Library()

@register.filter
def cache_pm_info(pms):         # ...
    ids = [x.id for x in pms]
    
    # ----- recipients -----
    recipient = MessageRecipient.objects.filter(message__in=ids).select_related('group')
    recipients = defaultdict(list)
    for x in recipient:
        recipients[x.message_id].append(x.group)
        
    print recipients
    print pms
    for pm in pms:
        print pm
        pm.cache_recipients = sorted(recipients[pm.id])

    return pms

# DEPRECATED
@register.filter
def recipientlink(r):
    if isinstance(r, User):
        return userlink(r)
    elif isinstance(r, Group):
        return r.data
    else:
        return r
