from django import template
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User, Group

from userprofile.templatetags.userprofile_tags import userlink

from pm.models import MessageContent, MessageRecipient

from collections import defaultdict


register = template.Library()

# TODO: replace with .prefetch_related() after switching to Django 1.4
# (but, this also updates `read` field...)
# user=None for outbox for now
def _cache_pm_info(pms, inbox, user):         # ...
    if inbox:
        msg_ids = [x.message_id for x in pms]
    else:
        msg_ids = [x.id for x in pms]
    
    # ----- groups -----
    #recipient = MessageRecipient.objects.filter(message__in=ids).select_related('group')
    pairs = MessageContent.groups.through.objects.filter(messagecontent__in=msg_ids).select_related('group')
    pm_groups = defaultdict(list)
    for x in pairs:
        pm_groups[x.messagecontent_id].append(x.group)
        
    if inbox:
        for pm in pms:
            pm.message.cache_recipients = sorted(pm_groups[pm.message_id])
    else:
        for pm in pms:
            pm.cache_recipients = sorted(pm_groups[pm.id])

    # ----- `read` field -----
    if inbox:
        read_recs = []
        for x in pms:
            if x.read: continue
            x.read = 0
            read_recs.append(x.id)
            
        if read_recs:
            MessageRecipient.objects.filter(id__in=read_recs).update(read=1)
            if user:
                profile = user.get_profile()
                profile.unread_pms = MessageRecipient.objects.filter(recipient=user, deleted=False, read=0).count()
                profile.save()
    
    return pms
    
@register.filter
def cache_inbox_info(pms, user):
    return _cache_pm_info(pms, True, user)

@register.filter
def cache_outbox_info(pms):
    return _cache_pm_info(pms, False, None)

# DEPRECATED
@register.filter
def recipientlink(r):
    if isinstance(r, User):
        return userlink(r)
    elif isinstance(r, Group):
        return r.data
    else:
        return r
