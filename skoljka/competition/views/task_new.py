from django.shortcuts import get_object_or_404

from skoljka.competition.decorators import competition_view
from skoljka.competition.forms import CompetitionTaskForm
from skoljka.competition.models import CompetitionTask
from skoljka.competition.utils import comp_url, create_ctask
from skoljka.permissions.constants import EDIT
from skoljka.utils.decorators import response

__all__ = ['task_new']


@competition_view(permission=EDIT)
@response('competition_task_new.html')
def task_new(request, competition, data, ctask_id=None):
    if ctask_id:
        ctask = get_object_or_404(
            CompetitionTask.objects.select_related('task'),
            id=ctask_id,
            competition_id=competition.id,
        )
        edit = True
    else:
        ctask = None
        edit = False

    POST = request.POST if request.method == 'POST' else None
    form = CompetitionTaskForm(
        POST, instance=ctask, competition=competition, user=request.user
    )

    if request.method == 'POST' and form.is_valid():
        ctask = form.save(commit=False)
        if not edit:
            ctask.competition = competition
            ctask.chain = None
            ctask.chain_position = -1  # Determine au

        create_ctask(
            ctask,
            request.user,
            competition,
            ctask._text,
            ctask._comment,
            name=form.cleaned_data.get('name'),
        )

        target = request.POST.get('next', 'stay')
        if target == 'next':
            return (comp_url(competition, 'task/new'),)
        if target == 'tasks':
            return (comp_url(competition, 'chain/tasks'),)
        return (ctask.get_edit_url(),)  # stay

    data['is_solution_hidden'] = ctask and ctask.task.author_id != request.user.id
    data['form'] = form
    data['ctask'] = ctask
    return data
