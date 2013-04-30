from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from search.forms import SearchForm, AdvancedSearchForm
from search.utils import search_tasks
from solution.views import get_user_solved_tasks
from tags.models import Tag
from tags.utils import get_available_tags, split_tags
from task.models import Task


def view(request):
    q = request.GET.get('q')

    if q is not None:
        q = split_tags(q)

    error = []
    tags = list(get_available_tags(q or []).values_list('name', flat=True))
    if q is not None:
        if not q:
            error.append('Navedite barem jednu oznaku!')
        elif len(tags) != len(q):
            diff = set([x.lower() for x in q]) - set([x.lower() for x in tags])
            error.append(u'Nepostojeć%s: %s!' % (
                u'a oznaka' if len(diff) == 1 else 'e oznake',
                u', '.join(diff),
            ))

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

    if not error:
        tasks = search_tasks(tags, user=request.user, **kwargs)
        if hasattr(tasks, 'select_related'):
            tasks = tasks.select_related('author', 'content')
    else:
        tasks = Task.objects.none()


    return render_to_response('search.html', {
        'tasks': tasks,
        'submitted_tasks' : get_user_solved_tasks(request.user),
        'tags': tags,
        'form': SearchForm(request.GET),
        'advanced_form': advanced_form,
        'search_solved_count': bool(kwargs.get('groups')),
        'any': bool(request.GET),
        'errors': '<br>'.join(error),
        }, context_instance=RequestContext(request))
