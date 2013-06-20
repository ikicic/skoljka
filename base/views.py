from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from activity.models import Action
from task.models import Task
from task.templatetags.task_tags import cache_task_info
from permissions.constants import VIEW
#from recommend.utils import refresh_user_information
from recommend.models import UserRecommendation

from skoljka.utils.decorators import response

import random

def homepage_offline(request, recent_tasks):
    folder_shortcuts = settings.FOLDER_HOMEPAGE_SHORTCUTS_OFFLINE

    return ('homepage_offline.html', {
        'recent_tasks': recent_tasks,
        'homepage': True,
        'folder_shortcut_desc': settings.FOLDER_HOMEPAGE_SHORTCUTS_OFFLINE,
        })

def homepage_online(request, recent_tasks):
    recommend = UserRecommendation.objects.raw(
        'SELECT A.id, A.task_id FROM recommend_userrecommendation A'        \
        '   LEFT JOIN solution_solution B'
        '       ON (A.task_id = B.task_id AND A.user_id = B.author_id)'     \
        '   WHERE A.user_id = {} AND (B.status IS NULL OR B.status = 0);'   \
        .format(request.user.id));
    recommend = list(x.task_id for x in recommend)

    if len(recommend) > 5:
        recommend = random.sample(recommend, 5)

    if recommend:
        recommend = Task.objects.filter(id__in=recommend)

        # context, tasks
        cache_task_info({'user': request.user}, recommend)

    return ('homepage_online.html', {
        'recent_tasks': recent_tasks,
        'recommend': recommend[1:],
        'best_recommend': None if len(recommend) < 1 else recommend[0],
        'homepage': True,
        'folder_shortcut_desc': settings.FOLDER_HOMEPAGE_SHORTCUTS_ONLINE,
        })


@response()
def homepage(request):
    recent_tasks = list(Task.objects.for_user(request.user, VIEW).distinct() \
        .order_by('-id')[:10])

    if len(recent_tasks) > 2:
        recent_tasks = random.sample(recent_tasks, 2)

    if request.user.is_authenticated():
        return homepage_online(request, recent_tasks)
    else:
        return homepage_offline(request, recent_tasks)
