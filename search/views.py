from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from search.utils import splitTags, searchTasks

def searchView(request, tags=None):
    tags = splitTags( tags )
    if request.GET.has_key('q'):
        tags.extend( request.GET['q'].split(',') )

    tasks = searchTasks(tags)
    
    return render_to_response('search.html', {
        'tasks': tasks,
        'tags': tags,
        },
        context_instance=RequestContext(request),
    )