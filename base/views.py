from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from task.models import Task
from permissions.constants import VIEW
from recommend.utils import refresh_user_information

import random

def homepage(request):
    tasks = list(Task.objects.for_user(request.user, VIEW).distinct().order_by('-id')[:10])
    random.shuffle(tasks)
    
    
    recommend = []
    if request.user.is_authenticated():
        refresh_user_information(request.user)
        recommend = list(request.user.recommendations.order_by('-userrecommendation__score')[:10])
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
    
    return render_to_response('homepage.html', {
        'latest_task': tasks[0],
        'recent_tasks': tasks[1:5],
        'recommend': recommend[1:],
        'best_recommend': None if len(recommend) < 1 else recommend[0],
        }, context_instance=RequestContext(request))
