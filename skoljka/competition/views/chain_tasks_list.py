from django.utils.translation import ugettext as _

from skoljka.competition.decorators import competition_view
from skoljka.competition.forms import ChainTasksForm
from skoljka.competition.models import Chain, CompetitionTask
from skoljka.competition.utils import (
    ctask_comment_verified_class,
    is_ctask_comment_important,
    refresh_chain_cache_is_verified,
    refresh_ctask_cache_admin_solved_count,
    refresh_ctask_cache_new_activities_count,
    refresh_submissions_score,
    update_chain_ctasks,
)
from skoljka.competition.views.utils_chain import init_categories_and_sort_chains
from skoljka.permissions.constants import EDIT
from skoljka.utils.decorators import response

__all__ = ['chain_tasks_list']


@competition_view(permission=EDIT)
@response('competition_chain_list_tasks.html')
def chain_tasks_list(request, competition, data):
    created = False
    updated_chains_count = None
    updated_ctasks_count = None
    updated_submissions_score_count = None
    empty_form = ChainTasksForm(competition=competition)
    form = empty_form

    if request.POST.get('action') == 'refresh-chain-cache-is-verified':
        updated_chains_count = len(refresh_chain_cache_is_verified(competition))
    elif request.POST.get('action') == 'refresh-ctask-cache-admin-solved-count':
        updated_ctasks_count = len(refresh_ctask_cache_admin_solved_count(competition))
    elif request.POST.get('action') == 'refresh-ctask-cache-new-activities-count':
        updated_ctasks_count = len(
            refresh_ctask_cache_new_activities_count(competition)
        )
    elif request.POST.get('action') == 'refresh-submission-is-correct':
        updated_submissions_score_count = refresh_submissions_score(
            competitions=[competition]
        )
    elif request.method == 'POST':
        form = ChainTasksForm(request.POST, competition=competition)
        if form.is_valid():
            chain = form.save(commit=False)
            chain.competition = competition
            chain.save()

            old_ids = CompetitionTask.objects.filter(chain=chain).values_list(
                'id', flat=True
            )
            new_ids = [x.id for x in form.cleaned_data['ctasks']]
            update_chain_ctasks(competition, chain, old_ids, new_ids)
            created = True
            form = empty_form  # Empty the form.

    chains = Chain.objects.filter(competition=competition)
    categories, chains = init_categories_and_sort_chains(
        competition,
        chains,
        request.LANGUAGE_CODE,
        sort_by=request.GET.get('sort', 'category'),
        sort_descending=request.GET.get('direction', 'asc') == 'desc',
    )

    chain_dict = {chain.id: chain for chain in chains}
    ctasks = list(
        CompetitionTask.objects.filter(competition=competition).select_related(
            'task__author', 'task__content__text', 'comment__text'
        )
    )

    for chain in chains:
        chain.competition = competition
        chain.t_ctasks = []

    unused_ctasks = []
    for ctask in ctasks:
        ctask.competition = competition
        if ctask.chain_id is None:
            unused_ctasks.append(ctask)
        else:
            chain_dict[ctask.chain_id].t_ctasks.append(ctask)

    for ctask in ctasks:
        is_important = ctask.comment.text.strip() and is_ctask_comment_important(
            ctask.comment.text
        )
        ctask.t_class = ctask_comment_verified_class(
            competition, ctask, request.user, is_important=is_important
        )

    for chain in chains:
        chain.t_ctasks.sort(key=lambda x: x.chain_position)
        chain.t_class = 'cchain-verified-list' if chain.cache_is_verified else ''

    data['created'] = created
    data['form'] = form
    data['chains'] = chains
    data['unused_ctasks'] = unused_ctasks
    data['trans_checked_title'] = _(
        "Number of admins that solved this task. (In parentheses: non-default max submissions)"
    )
    data['updated_chains_count'] = updated_chains_count
    data['updated_ctasks_count'] = updated_ctasks_count
    data['updated_submissions_score_count'] = updated_submissions_score_count
    return data
