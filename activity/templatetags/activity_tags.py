from django import template
from django.db.models import Q
from django.utils.safestring import mark_safe

from activity.constants import *
from activity.models import Action
from userprofile.templatetags.userprofile_tags import userlink

register = template.Library()

@register.simple_tag(takes_context=True)
def prepare_action_data(context, act):
    user = context['user']
    
    S = ''
    if act.type == TASK_ADD:
        S = u'je dodao/la novi zadatak'
    elif act.type == SOLUTION_SUBMIT:
        S = u'je poslao/la %s za zadatak' % act.A('solution', u'rješenje')
    elif act.type == SOLUTION_AS_SOLVED:
        S = u'je oznacio/la kao riješen zadatak'
    elif act.type == SOLUTION_TODO:
        S = u'je oznacio/la s To Do zadatak'
    elif act.type == GROUP_ADD:
        S = u'je dodao korisnika/cu %s u grupu %s' % (act.A('profile'), act.T('usergroup'))
    elif act.type == GROUP_LEAVE:
        S = u'je izašao/la iz grupe %s' % act.T('group')
    elif act.type == POST_SEND:
        your_task = u'tvoj ' if user.is_authenticated() and user.id == act.target_id else u''
        task = u'%szadatak %s' % (your_task, act.T('task'))
        if user.is_authenticated() and user.get_profile().private_group_id == act.group_id:
            act._label = ('label-info', 'Odgovor')
            S = u'je odgovorio/la na tvoj komentar na %s:' % task
        else:
            S = u'je poslao/la <a href="/task/%d/#post%d">komentar</a> na %s' % \
                (act.target_id, act.action_object_id, task)
        
    act._message = mark_safe(S)
    
    return u''


@register.inclusion_tag('inc_recent_activity.html', takes_context=True)
def activity_list(context, exclude_user=None, target=None, action_object=None): 
    user = context['user']

    # SPEED: maknuti nepotrebni JOIN auth_group ON (auth_group.id = action.group_id)
    activity = Action.objects.distinct()
    if user.is_authenticated():
        activity = activity.filter(Q(public=True) | Q(group__user=user))
    else:
        activity = activity.filter(public=True)
    
    if exclude_user and exclude_user.is_authenticated():
        activity = activity.exclude(actor=exclude_user)
    if target:
        activity = activity.filter(target=target)
    if action_object:
        activity = activity.filter(action_object=action_object)
        
    activity = activity.select_related('actor').order_by('-id')[:40]
    
    return {'activity': activity, 'user': user, 'request': context['request']}
