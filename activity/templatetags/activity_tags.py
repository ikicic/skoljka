from django import template
from django.utils.safestring import mark_safe

from userprofile.templatetags.userprofile_tags import userlink
from skoljka.utils.string_operations import G

from activity.constants import *
from activity.utils import get_recent_activities

register = template.Library()


@register.simple_tag(takes_context=True)
def prepare_action_data(context, A):
    user = context['user']

    gender = A.actor.get_profile().gender
    G1 = G('o', 'la', gender)

    ttype = (A.type, A.subtype)

    S = ''
    if ttype == TASK_ADD:
        S = u'je doda%s novi zadatak' % G1
    elif ttype == FILE_ADD:
        S = u'je doda%s novu datoteku' % G1
    elif ttype == SOLUTION_SUBMIT:
        link = u'rješenje' if getattr(A, '_hide_solution_link', False) \
            else A.A('solution', u'rješenje')
        S = u'je posla%s %s zadatka' % (G1, link)
    elif ttype == SOLUTION_AS_SOLVED:
        S = u'je označi%s kao riješen zadatak' % G1
    elif ttype == SOLUTION_TODO:
        S = u'je označi%s s To Do zadatak' % G1
    elif ttype == SOLUTION_AS_OFFICIAL:
        S = u'je postavi%s službeno %s zadatka' %    \
            (G1, A.A('solution', u'rješenje'))
    elif ttype == GROUP_ADD:
        S = u'je doda%s korisni%s %s u grupu %s' %   \
            (G1, G('ka', 'cu', gender), A.A('profile'), A.T('usergroup'))
    elif ttype == GROUP_LEAVE:
        S = u'je izaš%s iz grupe %s' % (G('ao', 'la', gender), A.T('usergroup'))
    elif ttype == POST_SEND or ttype == SOLUTION_RATE:
        # SOLUTION_RATE works similar to POST_SEND for Solution comments

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

            solution = u'rješenje' if getattr(A, '_hide_solution_link', False) \
                else A.T('solution', u'rješenje')
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

        if ttype == POST_SEND:
            if user.is_authenticated() and user.get_profile().private_group_id == A.group_id:
                A._label = ('label-info', 'Odgovor')
                S = u'je <a href="/%s/%d/#post%d">odgovori%s na tvoj komentar</a> na %s:' \
                    % (content_type.model, A.target_id, A.action_object_id, G1, object)
            else:
                S = u'je posla%s <a href="/%s/%d/#post%d">komentar</a> na %s' \
                    % (G1, content_type.model, A.target_id, A.action_object_id, object)
        else: # SOLUTION_RATE
            S = u'je ocijeni%s %s:' % (G1, object)

    A._message = mark_safe(S)

    return u''


@register.inclusion_tag('inc_recent_activity.html', takes_context=True)
def activity_list(context, exclude_user=None, target=None, action_object=None):
    """
        Output recent activities. Takes care of permissions and similar.
    """
    user = context['user']
    activity = get_recent_activities(user, 30, exclude_user=exclude_user,
        target=target, action_object=action_object)
    return {'activity': activity, 'user': user, 'request': context['request']}
