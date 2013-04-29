from django import template
from django.db.models import Q
from django.utils.safestring import mark_safe

from activity.constants import *
from activity.models import Action
from userprofile.templatetags.userprofile_tags import userlink

register = template.Library()

def G(male, female, gender):
    """
        (gender) Returns string male if user is male, female if female.
        If gender isn't given, returns both strings separated with '/'.
    """
    if gender == 'M':
        return male
    elif gender == 'F':
        return female
    return male + '/' + female

@register.simple_tag(takes_context=True)
def prepare_action_data(context, A):
    user = context['user']
    
    # TODO: finish this...
    # gender = ????
    gender = ''
    G1 = G('o', 'la', gender)

    ttype = (A.type, A.subtype)

    S = ''
    if ttype == TASK_ADD:
        S = u'je doda%s novi zadatak' % G1
    elif ttype == FILE_ADD:
        S = u'je doda%s novu datoteku' % G1
    elif ttype == SOLUTION_SUBMIT:
        S = u'je posla%s %s za zadatak' % (G1, A.A('solution', u'rješenje'))
    elif ttype == SOLUTION_AS_SOLVED:
        S = u'je označi%s kao riješen zadatak' % G1
    elif ttype == SOLUTION_TODO:
        S = u'je označi%s s To Do zadatak' % G1
    elif ttype == SOLUTION_AS_OFFICIAL:
        S = u'je postavi%s službeno %s za zadatak' %    \
            (G1, A.A('solution', u'rješenje'))
    elif ttype == GROUP_ADD:
        S = u'je dodao korisni%s %s u grupu %s' %   \
            (G('ka', 'cu', gender), A.A('profile'), A.T('usergroup'))
    elif ttype == GROUP_LEAVE:
        S = u'je izašao/la iz grupe %s' % A.T('group')
    elif ttype == POST_SEND:
    
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
            S = u'je odgovori%s na tvoj komentar na %s:' % (G1, object)
        else:
            S = u'je posla%s <a href="/%s/%d/#post%d">komentar</a> na %s' % \
                (G1, content_type.model, A.target_id, A.action_object_id, object)
        
    A._message = mark_safe(S)
    
    return u''


@register.inclusion_tag('inc_recent_activity.html', takes_context=True)
def activity_list(context, exclude_user=None, target=None, action_object=None): 
    user = context['user']

    # SPEED: maknuti nepotrebni JOIN auth_group ON (auth_group.id = action.group_id)
    activity = Action.objects.distinct()
    if user.is_authenticated():
        activity = activity.filter(Q(public=True)
            | Q(group_id__in=user.get_profile().get_group_ids()))
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
