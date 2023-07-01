from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from skoljka.search.forms import AdvancedSearchForm, SearchForm
from skoljka.search.utils import search_tasks
from skoljka.tags.models import Tag
from skoljka.tags.utils import get_available_tags, split_tags
from skoljka.task.models import Task


def view(request):
    q = request.GET.get('q')

    if q is not None:
        q = split_tags(q)

    error = []
    tags = list(get_available_tags(q or []).values_list('name', flat=True))
    if q is not None:
        if not q:
            error.append("Navedite barem jednu oznaku!")
        elif len(tags) != len(q):
            diff = set([x.lower() for x in q]) - set([x.lower() for x in tags])
            error.append(
                u"Nepostojeć%s: %s!"
                % (
                    u"a oznaka" if len(diff) == 1 else "e oznake",
                    u", ".join(diff),
                )
            )

    kwargs = dict(
        show_hidden='show_hidden' in request.GET,
        quality_min=request.GET.get('quality_min'),
        quality_max=request.GET.get('quality_max'),
        difficulty_min=request.GET.get('difficulty_min'),
        difficulty_max=request.GET.get('difficulty_max'),
    )

    groups_error = False
    if request.user.has_perm('advanced_search'):
        if request.GET.get('q') is not None:
            advanced_form = AdvancedSearchForm(request.GET, user=request.user)
            if advanced_form.is_valid():
                kwargs['groups'] = advanced_form.cleaned_data['groups']
            else:
                groups_error = True
        else:
            advanced_form = AdvancedSearchForm(user=request.user)
    else:
        advanced_form = None

    if not error:
        tasks = search_tasks(tags, user=request.user, **kwargs)
        if hasattr(tasks, 'select_related'):
            tasks = tasks.select_related('author', 'content')
    else:
        tasks = Task.objects.none()

    return render_to_response(
        'search.html',
        {
            'advanced_form': advanced_form,
            'any': bool(request.GET),
            'errors': '<br>'.join(error),
            'form': SearchForm(request.GET),
            'groups_error': groups_error,
            'search_solved_count': bool(kwargs.get('groups')),
            'tasks': tasks,
            'tags': tags,
        },
        context_instance=RequestContext(request),
    )
