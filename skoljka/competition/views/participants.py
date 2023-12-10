from datetime import datetime

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.translation import ugettext as _

from skoljka.competition.decorators import competition_view
from skoljka.competition.models import Team, TeamCategories
from skoljka.competition.utils import comp_url, refresh_teams_cache_score
from skoljka.permissions.constants import EDIT
from skoljka.utils.decorators import response

__all__ = ['participants', 'scoreboard', 'team_list_admin', 'team_list_admin_confirm']


@competition_view()
@response('competition_scoreboard.html')
def participants(request, competition, data):
    if not competition.is_course:
        return (competition.get_scoreboard_url(),)  # Go to /scoreboard/.

    return _team_list(request, competition, data)


@competition_view()
@response('competition_scoreboard.html')
def scoreboard(request, competition, data):
    if competition.is_course:
        return (competition.get_scoreboard_url(),)  # Go to /participants/.

    return _team_list(request, competition, data)


class TeamCategoryChange:
    def __init__(
        self, team_id, team_name, old_category_name, new_category_name, new_category_id
    ):
        self.team_id = team_id
        self.team_name = team_name
        self.new_category_id = new_category_id
        self.old_category_name = old_category_name
        self.new_category_name = new_category_name

    def __unicode__(self):
        return _(
            u"Change the category of the team \"%(team)s\" from \"%(old)s\" to \"%(new)s\"."
        ) % {
            'team': self.team_name,
            'old': self.old_category_name,
            'new': self.new_category_name,
        }


@competition_view(permission=EDIT)
@response('competition_team_list_admin.html')
def team_list_admin(request, competition, data):
    if request.method == 'POST':
        changes = _parse_team_list_admin_post(request, competition)
        if isinstance(changes, HttpResponse):
            return changes

        # TODO: Django 2.2: use bulk_update
        for change in changes:
            Team.objects.filter(id=change.team_id).update(
                category=change.new_category_id
            )
        return (request.get_full_path(),)

    return _team_list(request, competition, data)


@competition_view(permission=EDIT)
@response('competition_team_list_admin_confirmation.html')
def team_list_admin_confirm(request, competition, data):
    # Only POST makes sense here.
    if request.method != 'POST':
        return (comp_url(competition, 'team/list/admin'),)

    changes = _parse_team_list_admin_post(request, competition)
    if isinstance(changes, HttpResponse):
        return changes
    data['changes'] = changes
    return data


def _parse_team_list_admin_post(request, competition):
    team_categories = competition.parse_team_categories()
    if team_categories is None:
        return HttpResponse("Competition has no valid team_categories.")
    try:
        category_dict = team_categories.as_ordered_dict(request.LANGUAGE_CODE)
    except KeyError:
        return HttpResponse(
            "Team categories for the language '{}' not specified.".format(
                request.LANGUAGE_CODE
            )
        )

    def to_name(category_id):
        name = category_dict.get(category_id)
        if name is None:
            # This is visible only to admins, okay to show the ID.
            # (Contrary to team.t_category, which will be visible publicly.)
            return _(u"Invalid category #%d") % category_id
        return name

    teams = list(
        Team.objects.filter(competition=competition).values_list(
            'id', 'name', 'category'
        )
    )
    changes = []

    for team_id, name, old_category in teams:
        new_category = request.POST.get('team-{}-category'.format(team_id))
        if new_category is not None:
            try:
                new_category = int(new_category)
            except ValueError:
                return HttpResponseBadRequest()
            if new_category != old_category:
                changes.append(
                    TeamCategoryChange(
                        team_id,
                        name,
                        to_name(old_category),
                        to_name(new_category),
                        new_category,
                    )
                )

    return changes


def _team_list(request, competition, data):
    """Joint view for scoreboard and participants list.

    The two are identical, up to the default sorting and terminology.
    """

    if not competition.public_scoreboard and not data['is_admin']:
        return (competition.get_absolute_url(),)  # Redirect to home.

    if data['is_admin'] and 'refresh' in request.POST:
        start = datetime.now()
        teams = Team.objects.filter(competition=data['competition'])
        refresh_teams_cache_score(teams)
        data['refresh_calculation_time'] = datetime.now() - start

    extra = {} if data['is_admin'] else {'team_type': Team.TYPE_NORMAL}

    sort_by = request.GET.get('sort')
    if sort_by == 'actual_score' and data['is_admin']:
        order_by = '-cache_score'
    elif sort_by == 'category' and data['is_admin']:
        # Only for admins, because the sort is by ID, which is unintuitive.
        order_by = 'category'
    elif sort_by == 'name':
        order_by = 'name'
    elif sort_by == 'score':
        order_by = '-cache_score_before_freeze'
    elif competition.is_course:
        order_by = 'name'
    else:
        order_by = '-cache_score_before_freeze'

    teams = list(
        Team.objects.filter(competition=competition, **extra)
        .order_by(order_by, 'id')
        .only(
            'id',
            'name',
            'cache_score',
            'cache_score_before_freeze',
            'cache_max_score_after_freeze',
            'team_type',
            'category',
        )
    )

    try:
        categories = competition.parse_team_categories()
        categories_dict = categories.lang_to_categories[request.LANGUAGE_CODE]
        category_choices = categories.as_choices(request.LANGUAGE_CODE)
    except (AttributeError, KeyError):
        categories = TeamCategories()
        categories_dict = {}
        category_choices = []
    data['team_categories_title'] = u", ".join(categories_dict.values())

    last_score = -1
    last_position = 1
    position = 1
    for i, team in enumerate(teams):
        team.competition = competition
        if team.is_normal() and team.cache_score_before_freeze != last_score:
            last_position = position
        team.t_position = i + 1 if order_by == 'name' else last_position
        if category_choices:
            team.t_category = categories_dict.get(team.category)
            if team.t_category is None:
                team.t_is_category_valid = False
                # One will be publicly visible, so do not expose the number there.
                team.t_category = _("Invalid category")
                team.t_category_admin = _("Invalid category #%d") % team.category
            else:
                team.t_is_category_valid = True
        if team.is_normal():
            last_score = team.cache_score_before_freeze
            position += 1

    data['teams'] = teams
    data['as_participants'] = competition.is_course
    data['are_team_categories_visible'] = category_choices and not categories.hidden
    data['team_categories'] = category_choices
    return data
