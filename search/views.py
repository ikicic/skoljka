from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from task.models import Task

def search(request, tags=None):
    if type( tags ) is unicode:
        tags = tags.split(',')
    if type( tags ) is not list:
        tags = []
    if request.GET.has_key('q'):
        tags.extend( request.GET['q'].split(',') )
    tags = [x.strip() for x in tags]
    
    if tags:
        tasks = Task.objects.all()
        for tag in tags:
            tasks = tasks.filter(tags__name__iexact=tag)
    else:
        tasks = None
    
    return render_to_response('search.html', {
        'tasks': tasks,
        'tags': tags,
        },
        context_instance=RequestContext(request),
    )