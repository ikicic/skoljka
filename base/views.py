from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from activity.models import Action
from task.models import Task
from task.templatetags.task_tags import cache_additional_info as _task__cache_additional_info
from permissions.constants import VIEW
#from recommend.utils import refresh_user_information
from recommend.models import UserRecommendation

import random

def homepage(request):
    tasks = list(Task.objects.for_user(request.user, VIEW).distinct().order_by('-id')[:10])
    tasks = random.sample(tasks, 2)
    
    
    recommend = []
    if request.user.is_authenticated():
        #refresh_user_information(request.user)
        #recommend = list(request.user.recommendations.order_by('-userrecommendation__score'))
        recommend = list(UserRecommendation.objects.filter(user=request.user).values_list('task_id', flat=True))
#        distribution = request.user.profile.get_normalized_diff_distribution()
#        if distribution is not None:
#            dist = [0] * len(distribution)
#            for step in range(5):
#                choice = random.random()
#                for (k, x) in enumerate(distribution):
#                    if choice <= x:
#                        break;
#                    choice -= x
#                dist[k] += 1

#            for (k, x) in enumerate(dist):
#                if x == 0: continue
#                recommend.extend(Task.objects.filter(difficulty_rating_avg__range=(k - .5, k + .5)).order_by('?')[:x])
    if len(recommend) > 5:
        recommend = random.sample(recommend, 5)
    
    if recommend:
        recommend = Task.objects.filter(id__in=recommend)
        _task__cache_additional_info(recommend, request.user)

    # recommend = tasks = []
    return render_to_response('homepage.html', {
        'recent_tasks': tasks,
        'recommend': recommend[1:],
        'best_recommend': None if len(recommend) < 1 else recommend[0],
        }, context_instance=RequestContext(request))
