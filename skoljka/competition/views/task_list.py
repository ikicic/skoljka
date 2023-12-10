from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext

from skoljka.competition.decorators import competition_view
from skoljka.competition.forms import TaskListAdminPanelForm
from skoljka.competition.models import Chain, CompetitionTask, Submission
from skoljka.competition.utils import lock_ctasks_in_chain, preprocess_chain
from skoljka.competition.views.utils_chain import (
    init_categories_and_sort_chains,
    pick_name_translation,
)
from skoljka.utils.decorators import response

__all__ = ['task_list']


@competition_view()
@response('competition_task_list.html')
def task_list(request, competition, data):
    team = data['team']

    all_ctasks = list(CompetitionTask.objects.filter(competition=competition))
    all_ctasks_dict = {ctask.id: ctask for ctask in all_ctasks}
    if data['is_admin']:
        all_chains = list(
            Chain.objects.filter(competition=competition, cache_is_verified=True)
        )
    else:
        all_chains = list(
            Chain.objects.filter(
                competition=competition, cache_is_verified=True, restricted_access=False
            )
        )
        if team:
            all_chains += list(team.explicitly_accessible_chains.all())
    all_chains_dict = {chain.id: chain for chain in all_chains}

    if team:
        all_my_submissions = list(
            Submission.objects.filter(team=team).only(
                'id', 'ctask', 'score', 'oldest_unseen_admin_activity'
            )
        )
    else:
        all_my_submissions = []

    unverified_chains = set()
    for chain in all_chains:
        chain.ctasks = []
        chain.submissions = []
        chain.competition = competition  # Use preloaded object.

    for submission in all_my_submissions:
        ctask = all_ctasks_dict[submission.ctask_id]
        chain = all_chains_dict.get(ctask.chain_id)
        ctask.submission = submission
        if chain:
            chain.submissions.append(submission)

    for ctask in all_ctasks:
        submission = getattr(ctask, 'submission', None)
        if ctask.max_score > 1 or competition.is_course:
            if ctask.is_manually_graded() and submission:
                ctask.t_link_text = "{}/{}".format(
                    submission.score if submission else 0, ctask.max_score
                )
            else:
                ctask.t_link_text = str(ctask.max_score)
            ctask.t_title = (
                ungettext(
                    "This task is worth %d point.",
                    "This task is worth %d points.",
                    ctask.max_score,
                )
                % ctask.max_score
            )
        else:
            ctask.t_link_text = ""
            ctask.t_title = ""

        if (
            submission
            and submission.oldest_unseen_admin_activity
            != Submission.NO_UNSEEN_ACTIVITIES_DATETIME
        ):
            ctask.t_link_text = mark_safe(
                ctask.t_link_text + ' <i class="icon-comment"></i>'
            )
            ctask.t_title += " " + _("There are new messages.")

        if ctask.chain_id in all_chains_dict:
            chain = all_chains_dict[ctask.chain_id]
            ctask.chain = chain
            chain.ctasks.append(ctask)
        elif ctask.chain_id is not None:
            unverified_chains.add(ctask.chain_id)

    for chain in all_chains:
        chain.ctasks.sort(key=lambda ctask: ctask.chain_position)
        preprocess_chain(competition, chain, chain.ctasks, chain.submissions)

    for chain in all_chains:
        chain.t_is_locked = data['minutes_passed'] < chain.unlock_minutes
        chain.t_translated_name = pick_name_translation(
            chain.name, competition, request.LANGUAGE_CODE
        )

        chain.ctasks.sort(key=lambda ctask: (ctask.chain_position, ctask.id))
        if not data['has_finished']:
            lock_ctasks_in_chain(chain, chain.ctasks)
        else:
            for ctask in chain.ctasks:
                ctask.t_is_locked = False

        chain.t_next_task = None
        for ctask in chain.ctasks:
            if (
                not ctask.t_is_locked
                and not ctask.t_is_solved
                and ctask.t_submission_count < ctask.max_submissions
            ):
                chain.t_next_task = ctask
                break

    if not data['is_admin']:
        all_chains = [chain for chain in all_chains if not chain.t_is_locked]

    categories, all_chains = init_categories_and_sort_chains(
        competition,
        all_chains,
        request.LANGUAGE_CODE,
        sort_by='category',
        sort_descending=False,
    )

    if data['is_admin']:
        data['admin_panel_form'] = TaskListAdminPanelForm()
        for category in categories:
            category.t_is_locked = all(chain.t_is_locked for chain in category.chains)

    data['unverified_chains_count'] = len(unverified_chains)
    data['categories'] = categories
    data['max_chain_length'] = (
        0 if not all_chains else max(len(chain.ctasks) for chain in all_chains)
    )
    return data
