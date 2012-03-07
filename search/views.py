from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from search.forms import SearchForm, AdvancedSearchForm
from search.utils import search_tasks
from solution.views import get_user_solved_tasks

from taggit.utils import parse_tags


def view(request):
    tags = parse_tags(request.GET['q']) if 'q' in request.GET else []
    
    kwargs = dict(
        show_hidden = 'show_hidden' in request.GET,
        quality_min = request.GET.get('quality_min'),
        quality_max = request.GET.get('quality_max'),
        difficulty_min = request.GET.get('difficulty_min'),
        difficulty_max = request.GET.get('difficulty_max'),
    )
    
    if request.user.has_perm('advanced_search'):
        advanced_form = AdvancedSearchForm(request.GET)
        if advanced_form.is_valid():
            kwargs['groups'] = advanced_form.cleaned_data['groups']
    else:
        advanced_form = None

    tasks = search_tasks(tags, none_if_blank=False, user=request.user, **kwargs)
    if hasattr(tasks, 'select_related'):
        tasks = tasks.select_related('author')
        
    
    return render_to_response('search.html', {
        'tasks': tasks,
        'submitted_tasks' : get_user_solved_tasks(request.user),
        'tags': tags,
        'form': SearchForm(request.GET),
        'advanced_form': advanced_form,
        'search_solved_count': bool(kwargs.get('groups')),
        'any': bool(request.GET),
        }, context_instance=RequestContext(request))
