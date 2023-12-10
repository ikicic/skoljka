import django
from django.shortcuts import get_object_or_404

from skoljka.competition.decorators import competition_view
from skoljka.competition.forms import ChainForm
from skoljka.competition.models import Chain, ChainTeam, Team
from skoljka.permissions.constants import EDIT
from skoljka.utils.decorators import response

# TODO: When updating chain_position, update task name.
__all__ = ['chain_edit', 'chain_new']


@competition_view(permission=EDIT)
@response('competition_chain_new.html')
def chain_new(request, competition, data, chain_id=None):
    if chain_id:
        chain = get_object_or_404(Chain, id=chain_id, competition=competition)
        edit = True
    else:
        chain = None
        edit = False

    if request.method == 'POST' and 'change-chain-access' not in request.POST:
        chain_form = ChainForm(request.POST, competition=competition, instance=chain)
        if chain_form.is_valid():
            chain = chain_form.save(commit=False)
            if not edit:
                chain.competition = competition
            chain.save()

            return (chain.get_absolute_url(),)
    else:
        chain_form = ChainForm(competition=competition, instance=chain)

    if chain and chain.restricted_access:
        if _edit_teams_with_chain_access(request, competition, data, chain):
            return (chain.get_absolute_url(),)

    data['chain_form'] = chain_form
    data['chain'] = chain
    return data


def _edit_teams_with_chain_access(request, competition, data, chain):
    """Process the POST form handling chain access and load all teams and
    check which teams have access to the chain.

    Adds the following context item:
        has_team_categories: whether there are valid team categories
        teams: a list of modified Team objects, with two extra fields:
            team.t_has_chain_access: bool
            team.t_team_category_name: str

    Returns:
        True if a POST query was processed. False otherwise.
    """
    team_categories = competition.parse_team_categories()
    if team_categories is not None:
        category_names = team_categories.lang_to_categories.get(
            request.LANGUAGE_CODE, {}
        )
    else:
        category_names = {}

    # Always order by category, even if there are no team_categories specified
    # on the level of the competition. It is rare that this will be non-zero
    # anyway, but it may be useful to differentiate the teams while not
    # actually having any visible categories.
    teams = list(
        Team.objects.filter(competition=competition)
        .exclude(team_type=Team.TYPE_ADMIN_PRIVATE)
        .only('id', 'name', 'category')
        .order_by('category', 'name', 'id')
    )
    teams_with_access = set(
        ChainTeam.objects.filter(chain=chain).values_list('team_id', flat=True)
    )

    if request.method == 'POST' and 'change-chain-access' in request.POST:
        to_delete = []
        to_add = []
        for team in teams:
            has_access = team.id in teams_with_access
            should_have_access = 'team-{}'.format(team.id) in request.POST
            if has_access and not should_have_access:
                to_delete.append(team)
            elif not has_access and should_have_access:
                to_add.append(team)
        if to_delete:
            ChainTeam.objects.filter(chain=chain, team_id__in=to_delete).delete()
        if to_add:
            # TODO: Django 2.2 added ignore_conflicts to bulk_create.
            for team in to_add:
                try:
                    ChainTeam.objects.create(chain=chain, team=team)
                except django.db.IntegrityError:
                    pass  # Avoid race condition problems.
        return True  # Prevent form resubmission.

    for team in teams:
        team.t_category_name = category_names.get(team.category, str(team.category))
        team.t_has_chain_access = team.id in teams_with_access

    data['has_team_categories'] = bool(
        team_categories and team_categories.lang_to_categories
    )
    data['teams'] = teams
    return False


def chain_edit(request, competition_id, chain_id):
    return chain_new(request, competition_id, chain_id=chain_id)
