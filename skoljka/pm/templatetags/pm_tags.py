from collections import defaultdict

from django import template
from django.contrib.auth.models import Group, User

from skoljka.pm.models import MessageContent, MessageRecipient
from skoljka.userprofile.templatetags.userprofile_tags import userlink

register = template.Library()

# TODO: replace with .prefetch_related() after switching to Django 1.4
# (but, this also updates `read` field...)
# user=None for outbox for now
def _cache_pm_info(pms, type, user):  # ...
    if type == 'group_inbox':
        for x in pms:
            x.message = x.messagecontent
            x.message_id = x.messagecontent_id

    if type in ['inbox', 'group_inbox']:
        msg_ids = [x.message_id for x in pms]
    else:  # type == 'outbox':
        msg_ids = [x.id for x in pms]

    # ----- groups -----
    # recipient = MessageRecipient.objects.filter(message__in=ids).select_related('group')
    pairs = MessageContent.groups.through.objects.filter(
        messagecontent__in=msg_ids
    ).select_related('group')
    pm_groups = defaultdict(list)
    for x in pairs:
        pm_groups[x.messagecontent_id].append(x.group)

    if type in ['inbox', 'group_inbox']:
        for pm in pms:
            pm.message.cache_recipients = sorted(pm_groups[pm.message_id])
    else:  # type == 'outbox':
        for pm in pms:
            pm.cache_recipients = sorted(pm_groups[pm.id])

    # ----- `read` field -----
    if type == 'inbox':
        read_recs = []
        for x in pms:
            if x.read:
                continue
            x.read = 0
            read_recs.append(x.id)

        if read_recs:
            MessageRecipient.objects.filter(id__in=read_recs).update(read=1)
            if user:
                profile = user.get_profile()
                profile.unread_pms = MessageRecipient.objects.filter(
                    recipient=user, deleted=False, read=0
                ).count()
                profile.save()

    return pms


@register.simple_tag(takes_context=True)
def cache_inbox_info(context, pms):
    if context.get('group', None):
        _cache_pm_info(pms, 'group_inbox', context['user'])
    else:
        _cache_pm_info(pms, 'inbox', context['user'])
    return ''


@register.filter
def cache_outbox_info(pms):
    return _cache_pm_info(pms, 'outbox', None)


# DEPRECATED
@register.filter
def recipientlink(r):
    if isinstance(r, User):
        return userlink(r)
    elif isinstance(r, Group):
        return r.data
    else:
        return r
