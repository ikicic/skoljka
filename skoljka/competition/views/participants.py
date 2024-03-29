from collections import defaultdict
from datetime import datetime

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.http import urlencode
from django.utils.translation import ugettext as _

from skoljka.competition.decorators import competition_view
from skoljka.competition.models import Scoreboard, Team, TeamCategories
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
        category_dict = team_categories.lang_to_categories[request.LANGUAGE_CODE]
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


class ScoreboardTableEntry:
    """A single row in a scoreboard table."""

    def __init__(self, team, position):
        self.team = team
        self.position = position
        self.category = None
        self.category_admin = None
        self.is_category_valid = None


class ScoreboardTable:
    def __init__(self, entries, sort_key, title=None):
        self.entries = entries
        self.title = title
        self.sort_key = sort_key


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

    teams = list(
        Team.objects.filter(competition=competition, **extra).only(
            'id',
            'name',
            'cache_score',
            'cache_score_before_freeze',
            'cache_max_score_after_freeze',
            'team_type',
            'category',
        )
    )

    categories = competition.parse_team_categories()
    if not categories:
        categories = TeamCategories()
    categories_dict = categories.lang_to_categories.get(request.LANGUAGE_CODE, {})
    data['team_categories_title'] = u", ".join(categories_dict.values())

    for team in teams:
        team.competition = competition

    data['main_scoreboard'] = _make_scoreboard(
        request, competition, teams, categories_dict, data['is_admin'], sort_key='sort'
    )
    data['extra_scoreboards'] = _prepare_extra_scoreboards(
        request,
        competition,
        teams,
        categories_dict,
        categories.scoreboard,
        data['team'],
        data['is_admin'],
    )
    if data['extra_scoreboards']:
        # When `categories.hidden == True`, we need to show the team categories,
        # otherwise it wouldn't be clear what the extra tables are for.
        # However, it turns out that even with `categories.hidden == False`
        # only showing tables efeels weird. So we add the titles whenever extra
        # scoreboards are shown.
        data['main_scoreboard'].title = competition.get_team_metaname_plural_all
        for scoreboard in data['extra_scoreboards']:
            if scoreboard.entries:  # Just in case (we expect this to be non-empty).
                scoreboard.title = scoreboard.entries[0].category

    all_sort_keys = [scoreboard.sort_key for scoreboard in data['extra_scoreboards']]
    all_sort_keys.append(data['main_scoreboard'].sort_key)
    url_prefix = competition.get_scoreboard_url() + '?'
    data['sort_all_by_score_url'] = url_prefix + urlencode(
        {key: 'score' for key in all_sort_keys}
    )
    data['sort_all_by_actual_score_url'] = url_prefix + urlencode(
        {key: 'actual_score' for key in all_sort_keys}
    )

    data['teams'] = teams
    data['as_participants'] = competition.is_course
    data['are_team_categories_visible'] = categories_dict and not categories.hidden
    data['categories_dict'] = categories_dict
    return data


def _make_scoreboard(request, competition, teams, categories_dict, is_admin, sort_key):
    order_by = _get_order_by(request, sort_key)
    _inplace_sort_teams(competition, teams, order_by, is_admin)

    last_score = -1
    last_position = 1
    position = 1
    entries = []
    for i, team in enumerate(teams):
        if team.is_normal() and team.cache_score_before_freeze != last_score:
            last_position = position

        team_position = i + 1 if order_by == 'name' else last_position
        entry = ScoreboardTableEntry(team, team_position)

        if categories_dict:
            entry.category = categories_dict.get(team.category)
            if entry.category is None:
                entry.is_category_valid = False
                # Category will be publicly visible, so do not expose the number there.
                entry.category = _("Invalid category")
                entry.category_admin = _("Invalid category #%d") % team.category
            else:
                entry.is_category_valid = True
        if team.is_normal():
            last_score = team.cache_score_before_freeze
            position += 1

        entries.append(entry)

    return ScoreboardTable(entries, sort_key)


def _get_order_by(request, sort_key):
    """Return the order_by according to the GET parameter given by the `sort_key`
    variable, or (with a lower priority), the `sortall` key, or `None`."""
    order_by = request.GET.get(sort_key)
    if order_by is None:
        order_by = request.GET.get('sortall')
    return order_by


def _inplace_sort_teams(competition, teams, order_by, is_admin):
    """Sort the teams according to the given order_by."""
    if order_by == 'actual_score' and is_admin:
        teams.sort(key=lambda team: (-team.cache_score, team.id))
    elif order_by == 'category' and is_admin:
        teams.sort(key=lambda team: (team.category, team.id))
    elif order_by == 'name':
        teams.sort(key=lambda team: (team.name, team.id))
    elif order_by == 'score':
        teams.sort(key=lambda team: (-team.cache_score_before_freeze, team.id))
    elif competition.is_course:
        teams.sort(key=lambda team: (team.name, team.id))
    else:
        teams.sort(key=lambda team: (-team.cache_score_before_freeze, team.id))


def _prepare_extra_scoreboards(
    request, competition, teams, categories_dict, scoreboard, my_team, is_admin
):
    """Prepare the scoreboards that are shown next to the main scoreboard.
    Returns a list of scoreboards. Each scoreboard is a list of teams.

    Types of scoreboards:
        ALL: only the main scoreboard shown
        ALL_AND_NONZERO_MY: the main scoreboard + scoreboard of my team category, if non-zero
        ALL_AND_NONZERO_EACH: the main scoreboard + one scoreboard per non-zero team category
        ALL_AND_NONZERO_MY_THEN_REST: same as ALL_AND_NONZERO_EACH, with my being on top, if non-zero
    """
    if scoreboard == Scoreboard.ALL_AND_NONZERO_MY:
        if my_team and my_team.category != 0:
            filtered_teams = [t for t in teams if t.category == my_team.category]
            scoreboard = _make_scoreboard(
                request,
                competition,
                filtered_teams,
                categories_dict,
                is_admin,
                sort_key='sort{}'.format(my_team.category),
            )
            return [scoreboard]
        else:
            return []  # No side scoreboards.
    elif (
        scoreboard == Scoreboard.ALL_AND_NONZERO_EACH
        or scoreboard == Scoreboard.ALL_AND_NONZERO_MY_THEN_REST
    ):
        team_groups = defaultdict(list)
        for team in teams:
            if team.category != 0:
                team_groups[team.category].append(team)

        team_groups = list(team_groups.items())
        if my_team and scoreboard == Scoreboard.ALL_AND_NONZERO_MY_THEN_REST:
            # Put my team at the top.
            team_groups.sort(key=lambda item: (item[0] != my_team.category, item[0]))
        else:
            team_groups.sort(key=lambda item: item[0])

        return [
            _make_scoreboard(
                request,
                competition,
                team_group,
                categories_dict,
                is_admin,
                sort_key='sort{}'.format(category),
            )
            for category, team_group in team_groups
        ]
    else:
        return []  # No side scoreboards.
