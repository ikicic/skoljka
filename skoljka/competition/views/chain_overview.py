from django.shortcuts import get_object_or_404

from skoljka.competition.decorators import competition_view
from skoljka.competition.models import Chain, CompetitionTask
from skoljka.permissions.constants import EDIT
from skoljka.utils.decorators import response

__all__ = ['chain_overview']


@competition_view(permission=EDIT)
@response('competition_chain_overview.html')
def chain_overview(request, competition, data, chain_id):
    chain = get_object_or_404(Chain, id=chain_id, competition_id=competition.id)
    chain.competition = competition
    ctasks = (
        CompetitionTask.objects.filter(chain=chain)
        .select_related('task__content', 'task__author', 'comment')
        .order_by('chain_position')
    )
    for ctask in ctasks:
        ctask.competition = competition

    data['chain'] = chain
    data['ctasks'] = ctasks
    return data
