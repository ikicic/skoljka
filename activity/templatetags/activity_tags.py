from django import template
from django.db.models import Q
from django.utils.safestring import mark_safe

from activity.constants import *
from activity.models import Action
from userprofile.templatetags.userprofile_tags import userlink

register = template.Library()

@register.simple_tag(takes_context=True)
def prepare_action_data(context, A):
    user = context['user']
    
    S = ''
    if A.type == TASK_ADD:
        S = u'je dodao/la novi zadatak'
    elif A.type == SOLUTION_SUBMIT:
        S = u'je poslao/la %s za zadatak' % A.A('solution', u'rješenje')
    elif A.type == SOLUTION_AS_SOLVED:
        S = u'je oznacio/la kao riješen zadatak'
    elif A.type == SOLUTION_TODO:
        S = u'je oznacio/la s To Do zadatak'
    elif A.type == GROUP_ADD:
        S = u'je dodao korisnika/cu %s u grupu %s' % (A.A('profile'), A.T('usergroup'))
    elif A.type == GROUP_LEAVE:
        S = u'je izašao/la iz grupe %s' % A.T('group')
    elif A.type == POST_SEND:
    
        # ovisno o tipu targeta (zadatak, rjesenje), onoga na sto je zakacen post
        # razno se pristupa podacima
        content_type = A.target_content_type
        if content_type.app_label == 'task' and content_type.model == 'task':
            your_task = u'tvoj ' if user.id == A.target_id else u''
            object = u'%szadatak %s' % (your_task, A.T('task'))
        else: # content_type.app_label == 'solution' and content_type.model == 'solution':
        
            # za Task je jednostavno, ali nastaju problemi kod Solution
            # zato sto se jako puno podataka treba zapamtiti
            try:
                solution_author_id, solution_author_username, task_id, task_name, task_author_id = A.target_cache.split(POST_SEND_CACHE_SEPARATOR)
            except ValueError:
                solution_author_id, solution_author_username, task_id, task_name, task_author_id = -1, '{{ error }}', -1, '{{ error }}', -1
                
            solution = u'<a href="/solution/%d/">rješenje</a>' % A.target_id
            task = u'<a href="/task/%s/">%s</a>' % (task_id, task_name)
            
            if user.id == int(task_author_id):
                whose_task = ' tvoj'
            elif A.actor_id == int(task_author_id):
                whose_task = ' svoj'
            else:
                whose_task = ''
                
            if user.id == int(solution_author_id):
                whose_solution = 'tvoje %s'
            elif A.actor_id == int(solution_author_id):
                whose_solution = 'svoje %s'
            else:
                whose_solution = u'%%s korisnika <a href="/profile/%s/">%s</a>' % (solution_author_id, solution_author_username)

            object = u'%s za%s zadatak %s' % (whose_solution % solution, whose_task, task)
            
        if user.is_authenticated() and user.get_profile().private_group_id == A.group_id:
            A._label = ('label-info', 'Odgovor')
            S = u'je odgovorio/la na tvoj komentar na %s:' % object
        else:
            S = u'je poslao/la <a href="/%s/%d/#post%d">komentar</a> na %s' % \
                (content_type.model, A.target_id, A.action_object_id, object)
        
    A._message = mark_safe(S)
    
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
        
    activity = activity.select_related('actor', 'target_content_type').order_by('-id')[:40]
    
    return {'activity': activity, 'user': user, 'request': context['request']}
