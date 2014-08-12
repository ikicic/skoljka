from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from activity.models import Action
from permissions.constants import VIEW
from recommend.models import UserRecommendation
from solution.models import Solution, STATUS
from task.models import Task
from task.templatetags.task_tags import cache_task_info
from task.utils import check_prerequisites_for_tasks

from skoljka.libs.decorators import response

import random

def homepage_offline(request, recent_tasks):
    folder_shortcuts = settings.FOLDER_HOMEPAGE_SHORTCUTS_OFFLINE

    return ('homepage_offline.html', {
        'homepage': True,
        'folder_shortcut_desc': settings.FOLDER_HOMEPAGE_SHORTCUTS_OFFLINE,
        'recent_tasks': recent_tasks,
        })

def homepage_online(request, recent_tasks):
    recommend = UserRecommendation.objects.raw(
        'SELECT A.id, A.task_id FROM recommend_userrecommendation A'        \
        '   LEFT JOIN solution_solution B'                                  \
        '       ON (A.task_id = B.task_id AND A.user_id = B.author_id)'     \
        '   WHERE A.user_id = {} AND (B.status IS NULL OR B.status = 0);'   \
        .format(request.user.id));
    recommend = list(x.task_id for x in recommend)
    if len(recommend) > 4:
        recommend = random.sample(recommend, 4)
    else:
        recommend = [] # Simplify design, accept only if there are 4 tasks.

    todo = Solution.objects.filter(author=request.user, status=STATUS['todo']) \
            .values_list('task_id', flat=True)[:20]
    if len(todo) > 2:
        todo = random.sample(todo, 2)
    else:
        todo = [] # Simplify design, ignore if only one to do task.

    all_tasks_to_read = todo + recommend
    if all_tasks_to_read:
        all_tasks = Task.objects.select_related('content') \
                .in_bulk(all_tasks_to_read)

        # Just in case something went wrong (probably with recommendations).
        check_prerequisites_for_tasks(all_tasks.itervalues(), request.user)
        all_tasks = {id: task \
                for id, task in all_tasks.iteritems() \
                if task.cache_prerequisites_met}

        recommend = [all_tasks[id] for id in recommend]
        todo = [all_tasks[id] for id in todo]

    # context, tasks
    cache_task_info({'user': request.user}, recommend + recent_tasks)

    return ('homepage_online.html', {
        'homepage': True,
        'folder_shortcut_desc': settings.FOLDER_HOMEPAGE_SHORTCUTS_ONLINE,
        'recent_tasks': recent_tasks,
        'recommend': recommend,
        'todo': todo,
        })


@response()
def homepage(request):
    recent_tasks = list(Task.objects.for_user(request.user, VIEW)   \
        .select_related('content').order_by('-id')[:10])

    check_prerequisites_for_tasks(recent_tasks, request.user)

    # Filter visible tasks
    recent_tasks = [x for x in recent_tasks if x.cache_prerequisites_met]

    if len(recent_tasks) > 2:
        recent_tasks = random.sample(recent_tasks, 2)

    if request.user.is_authenticated():
        return homepage_online(request, recent_tasks)
    else:
        return homepage_offline(request, recent_tasks)
