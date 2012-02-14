from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from task.models import Task
from permissions.constants import VIEW

import random

def homepage(request):
    tasks = list(Task.objects.for_user(request.user, VIEW).distinct().order_by('-id')[:10])
    random.shuffle(tasks)
    
    return render_to_response('homepage.html', {
        'latest_task': tasks[0],
        'recent_tasks': tasks[1:5],
        }, context_instance=RequestContext(request))
