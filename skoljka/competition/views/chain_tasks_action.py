import re

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from skoljka.competition.decorators import competition_view
from skoljka.competition.forms import clean_unused_ctask_ids
from skoljka.competition.models import Chain, CompetitionTask
from skoljka.competition.utils import (
    comp_url,
    delete_chain,
    detach_ctask_from_chain,
    update_chain_ctasks,
)
from skoljka.permissions.constants import EDIT
from skoljka.utils.decorators import require, response

__all__ = ['chain_tasks_action']


@require(post=['action'])
@competition_view(permission=EDIT)
@response()
def chain_tasks_action(request, competition, data):
    action = request.POST['action']
    url_suffix = ""
    if re.match(r'delete-chain-(\d+)', action):
        # Delete whole chain. Does not delete ctasks, of course.
        id = int(action[len('delete-chain-') :])
        chain = get_object_or_404(Chain, id=id, competition=competition)
        delete_chain(chain)
    elif re.match(r'detach-(\d+)', action):
        # Detach ctask from a chain.
        id = int(action[len('detach-') :])
        ctask = get_object_or_404(CompetitionTask, id=id, competition=competition)
        url_suffix = '#chain-{}'.format(ctask.chain_id)
        detach_ctask_from_chain(ctask)
    elif action == 'add-after':
        # Add tasks at the beginning of a chain or after a given ctask.
        try:
            ctask_ids = request.POST['ctask-ids']
            after_what = request.POST['after-what']
            after_id = request.POST['after-id']
        except KeyError as e:
            return (400, "POST arguments missing {}".format(e))
        if after_what == 'chain':
            chain = get_object_or_404(Chain, id=after_id, competition=competition)
            position = 0
        elif after_what == 'ctask':
            ctask = get_object_or_404(
                CompetitionTask.objects.select_related('chain'),
                id=after_id,
                competition=competition,
            )
            chain = ctask.chain
            position = ctask.chain_position - 1
        else:
            return (400, "after_what={}?".format(after_what))
        old_ids = list(
            CompetitionTask.objects.filter(chain=chain)
            .order_by('chain_position')
            .values_list('id', flat=True)
        )
        try:
            selected_ids, selected_ctasks = clean_unused_ctask_ids(
                competition, ctask_ids
            )
        except ValidationError:
            return (400, "invalid ctask_ids: {}".format(ctask_ids))

        new_ids = old_ids[:position] + selected_ids + old_ids[position:]
        update_chain_ctasks(competition, chain, old_ids, new_ids)
        url_suffix = '#chain-{}'.format(chain.id)
    elif re.match(r'move-(lo|hi)-(\d+)', action):
        id = int(action[len('move-lo-') :])
        ctask = get_object_or_404(
            CompetitionTask.objects.select_related('chain'),
            id=id,
            competition=competition,
        )
        old_ids = list(
            CompetitionTask.objects.filter(chain=ctask.chain)
            .order_by('chain_position')
            .values_list('id', flat=True)
        )
        # FIXME: Explain why chain_position is 1-based.
        pos = ctask.chain_position - 1
        new_ids = old_ids[:]
        if action[5] == 'l' and pos > 0:
            new_ids[pos], new_ids[pos - 1] = new_ids[pos - 1], new_ids[pos]
        elif action[5] == 'h' and pos < len(old_ids) - 1:
            new_ids[pos], new_ids[pos + 1] = new_ids[pos + 1], new_ids[pos]
        else:
            # It could be that chain_positions are non-unique, so call
            # Call `update_chain_ctasks` to refresh them.
            pass

        url_suffix = '#chain-{}'.format(ctask.chain.id)
        update_chain_ctasks(competition, ctask.chain, old_ids, new_ids)
    else:
        return (400, "Unrecognized action " + action)
    return (comp_url(competition, "chain/tasks") + url_suffix,)
