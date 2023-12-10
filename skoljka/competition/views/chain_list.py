from django.contrib.auth.models import User
from django.db.models import F
from django.utils.safestring import mark_safe

from skoljka.competition.decorators import competition_view
from skoljka.competition.models import Chain, CompetitionTask, Submission, Team
from skoljka.competition.views.utils_chain import init_categories_and_sort_chains
from skoljka.permissions.constants import EDIT
from skoljka.utils.decorators import response

__all__ = ['chain_list']


@competition_view(permission=EDIT)
@response('competition_chain_list.html')
def chain_list(request, competition, data):
    chains = Chain.objects.filter(competition=competition)
    categories, chains = init_categories_and_sort_chains(
        competition,
        chains,
        language_code=None,
        sort_by=request.GET.get('sort', 'category'),
        sort_descending=request.GET.get('direction', 'asc') == 'desc',
    )
    chain_dict = {chain.id: chain for chain in chains}
    ctasks = list(
        CompetitionTask.objects.filter(competition=competition).values_list(
            'id', 'chain_id', 'task__author_id'
        )
    )
    author_ids = [author_id for ctask_id, chain_id, author_id in ctasks]
    authors = User.objects.only('id', 'username', 'first_name', 'last_name').in_bulk(
        set(author_ids)
    )

    verified_ctask_ids = set(
        Submission.objects.filter(
            team__competition_id=competition.id,
            team__team_type=Team.TYPE_ADMIN_PRIVATE,
            score=F('ctask__max_score'),
        ).values_list('ctask_id', flat=True)
    )

    for chain in chains:
        chain.competition = competition
        chain.t_ctask_count = 0
        chain._author_ids = set()
        # TODO: remove t_is_verified and use cache_is_verified?
        chain.t_is_verified = True

    for ctask_id, chain_id, author_id in ctasks:
        if chain_id is None:
            continue
        chain = chain_dict[chain_id]
        chain.t_ctask_count += 1
        chain._author_ids.add(author_id)
        if ctask_id not in verified_ctask_ids:
            chain.t_is_verified = False

    from skoljka.userprofile.templatetags.userprofile_tags import userlink

    for chain in chains:
        chain.t_authors = mark_safe(
            u", ".join(userlink(authors[author_id]) for author_id in chain._author_ids)
        )

    data['chains'] = chains
    return data
