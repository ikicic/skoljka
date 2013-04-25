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


def homepage(request):
    # TODO: cache this query
    recent_tasks = list(Task.objects.for_user(request.user, VIEW).distinct().order_by('-id')[:10])
    if len(recent_tasks) > 2:
        recent_tasks = random.sample(recent_tasks, 2)

    recommend = []
    if request.user.is_authenticated():
        recommend = list(UserRecommendation.objects.filter(user=request.user).values_list('task_id', flat=True))

    if len(recommend) > 5:
        recommend = random.sample(recommend, 5)

    if recommend:
        recommend = Task.objects.filter(id__in=recommend)

        # context, tasks
        cache_task_info({'user': request.user}, recommend)

    if request.user.is_authenticated():
        folder_shortcuts = settings.FOLDER_HOMEPAGE_SHORTCUTS
    else:
        folder_shortcuts = settings.FOLDER_HOMEPAGE_SHORTCUTS_OFFLINE

    return render_to_response('homepage.html', {
        'recent_tasks': recent_tasks,
        'recommend': recommend[1:],
        'best_recommend': None if len(recommend) < 1 else recommend[0],
        'homepage': True,
        'folder_shortcut_desc': folder_shortcuts,
        }, context_instance=RequestContext(request))
