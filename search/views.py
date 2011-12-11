from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from search.utils import search_tasks
from solution.views import get_user_solved_tasks

from taggit.utils import parse_tags


def searchView(request, tags=None):
    tags = parse_tags(tags)
    if request.GET.has_key('q'):
        tags.extend(parse_tags(request.GET['q']))

    tasks = search_tasks(tags).select_related('author')
    
    return render_to_response('search.html', {
        'tasks': tasks,
        'submitted_tasks' : get_user_solved_tasks(request.user),
        'tags': tags,
        }, context_instance=RequestContext(request))