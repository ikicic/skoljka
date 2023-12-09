import re
from datetime import datetime

import django
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import F
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext

from skoljka.activity import action as _action
from skoljka.competition.decorators import competition_view
from skoljka.competition.evaluator import (
    get_evaluator,
    get_sample_solution,
    get_solution_help_text,
    safe_parse_descriptor,
)
from skoljka.competition.forms import (
    ChainForm,
    ChainTasksForm,
    CompetitionSolutionForm,
    CompetitionTaskForm,
    TaskListAdminPanelForm,
    TeamForm,
    clean_unused_ctask_ids,
)
from skoljka.competition.models import (
    Chain,
    ChainTeam,
    Competition,
    CompetitionTask,
    Submission,
    Team,
    TeamCategories,
    TeamMember,
)
from skoljka.competition.templatetags.competition_tags import get_submission_actions
from skoljka.competition.utils import (
    comp_url,
    create_ctask,
    ctask_comment_verified_class,
    delete_chain,
    detach_ctask_from_chain,
    get_teams_for_user_ids,
    is_ctask_comment_important,
    load_and_preprocess_chain,
    lock_ctasks_in_chain,
    preprocess_chain,
    refresh_chain_cache_is_verified,
    refresh_ctask_cache_admin_solved_count,
    refresh_ctask_cache_new_activities_count,
    refresh_submissions_score,
    refresh_teams_cache_score,
    update_chain_ctasks,
    update_ctask_cache_admin_solved_count,
    update_score_on_ctask_action,
)
from skoljka.mathcontent.forms import MathContentForm
from skoljka.mathcontent.latex import latex_escape
from skoljka.permissions.constants import EDIT, VIEW
from skoljka.post.forms import PostsForm
from skoljka.post.models import Post
from skoljka.userprofile.forms import AuthenticationFormEx
from skoljka.utils.decorators import require, response

# [order=-10] asdf --> ('-10', ' asdf')
_CATEGORY_RE = re.compile(r'\[order=([-+]?\d+)\](.+)')


class _Category(object):
    """
    Helper class representing a chain category.

    Attribute `name` is a string of one of the following formats:
        "name"
        "name for language 1 | name for language 2"
        "[order=123] name"
        "[order=123] name | name"              <-- same order for all languages
        "[order=123] name | [order=132] name"  <-- custom order per language

    The order number may be negative.
    """

    def __init__(self, name, competition, lang, category_translations):
        translated_name = pick_name_translation(name, competition, lang)
        order, translated_name = self.split_order_name(translated_name)
        if order is None:
            # If there was no [order=...] for the current language, check if it
            # was specified for the first language.
            order, _ = self.split_order_name(name)
            if order is None:
                order = 0

        translated_name = translated_name.strip()
        if category_translations:  # Legacy, deprecated.
            translated_name = category_translations.get(
                translated_name, translated_name
            )

        self.name = name
        self.order = order
        self.translated_name = translated_name
        self.chains = []
        self.t_is_locked = None

    @property
    def sort_key(self):
        return (self.order, self.translated_name)

    @staticmethod
    def split_order_name(name):
        """Split a string "[order=213] Name" into a tuple (123, "Name").

        If there is no valid "[order=...]" prefix, (None, name) is returned
        instead.
        """
        match = _CATEGORY_RE.match(name)
        if match:
            try:
                order, name = match.groups()
                order = int(order)
                return order, name
            except:  # noqa: E722 do not use bare 'except'
                pass
        return None, name


def _init_categories_and_sort_chains(
    competition, chains, language_code, sort_by='category', sort_descending=False
):
    """Find unique categories, fill chain.t_category and sort chains.

    Attributes:
        chains: a sequence of Chain objects
        competition: a Competition object
        language_code: an optional string representing the language
        sort_by: 'category' or 'unlock_minutes', 'category' by default
        sort_descending: whether to sort in the reverse order, False by default

    Returns a tuple (sorted categories list, sorted chains list).
    Note that if chains are not sorted according to the category, the category
    sorting will be unrelated to the sorting of chains.
    """
    chains = list(chains)

    # First sort by position and name, such that they are appended to
    # categories in the correct order.
    chains.sort(key=lambda chain: (chain.position, chain.name))

    # Deprecated.
    category_translations = competition.get_task_categories_translations(language_code)

    categories = {}
    for chain in chains:
        category = categories.get(chain.category)
        if not category:
            category = categories[chain.category] = _Category(
                chain.category, competition, language_code, category_translations
            )
        chain.t_category = category
        category.chains.append(chain)

    # Once categories are known, sort either by categories or by
    # unlock_minutes. The sort is stable.
    if sort_by == 'unlock_minutes':
        chains.sort(key=lambda chain: chain.unlock_minutes)
    else:
        chains.sort(key=lambda chain: chain.t_category.sort_key)

    categories = list(categories.values())
    categories.sort(key=lambda cat: cat.sort_key)

    if sort_descending:
        chains = chains[::-1]
        categories = categories[::-1]

    return categories, chains


# TODO: Option for admins to create a team even if they have a private group.
# TODO: When updating chain_position, update task name.
# TODO: Formalize when update_ does .save() or not.


@response('competition_list.html')
def competition_list(request, kind=Competition.KIND_COMPETITION):
    competitions = (
        Competition.objects.for_user(request.user, VIEW)
        .filter(kind=kind)
        .distinct()
        .order_by('-start_date', '-id')
    )
    member_of = list(
        TeamMember.objects.filter(
            member_id=request.user.id, invitation_status=TeamMember.INVITATION_ACCEPTED
        ).values_list('team__competition_id', flat=True)
    )

    return {
        'kind_name': Competition.KIND[kind],
        'competitions': competitions,
        'current_time': datetime.now(),
        'member_of': member_of,
    }


def course_list(request):
    return competition_list(request, kind=Competition.KIND_COURSE)


@competition_view()
@response('competition_homepage.html')
def homepage(request, competition, data):
    return data


def _update_team_invitations(team, team_form):
    old_invitations = list(TeamMember.objects.filter(team=team))
    old_invitations_dict = {x.member_id: x for x in old_invitations if x.member_id}

    author = team.author
    members = team_form.other_members
    members.append((author.username, author))  # Author is also a member
    new_invited_users_ids = set(user.id for name, user in members if user)

    # Delete old invitations (keep old TeamMember instances if necessary).
    for invitation in old_invitations:
        if (
            invitation.member_id is None
            or invitation.member_id not in new_invited_users_ids
        ):
            invitation.delete()

    # Insert new invitations (don't duplicate TeamMember).
    for name, user in members:
        if not user or user.id not in old_invitations_dict:
            status = (
                TeamMember.INVITATION_ACCEPTED
                if not user or user.id == author.id
                else TeamMember.INVITATION_UNANSWERED
            )
            TeamMember.objects.create(
                team=team, member=user, member_name=name, invitation_status=status
            )


@competition_view()
@response('competition_team_detail.html')
def team_detail(request, competition, data, team_id):
    data['preview_team'] = get_object_or_404(
        Team, id=team_id, competition_id=competition.id
    )
    data['preview_team_members'] = (
        TeamMember.objects.filter(
            team_id=team_id, invitation_status=TeamMember.INVITATION_ACCEPTED
        )
        .select_related('member')
        .order_by('member_name')
    )
    if data['is_admin']:
        data['submissions'] = list(
            Submission.objects.filter(team_id=team_id)
            .select_related('ctask', 'ctask__chain__name')
            .order_by('id')
        )
        for submission in data['submissions']:
            if submission.ctask.chain_id:
                submission.ctask.chain.competition = competition
            submission.ctask.competition = competition
    return data


@competition_view()
@response('competition_registration.html')
def registration(request, competition, data):
    team = data['team']
    if data['has_finished']:
        if team:
            return (team.get_absolute_url(),)
        else:
            return (competition.get_absolute_url(),)

    if (
        competition.registration_open_date > data['current_time']
        and not data['is_admin']
    ):
        return (competition.get_absolute_url(),)
    if not request.user.is_authenticated():
        data['form'] = AuthenticationFormEx()
        return 'competition_registration_login.html', data

    if team and not competition.are_teams_editable:
        return (team.get_absolute_url(),)

    team_form = None
    if request.method == 'POST':
        action = _handle_registration_post_request(request, competition, data)
        if isinstance(action, TeamForm):
            team_form = action
        elif action:
            return action

    if (
        team_form is None
        and not (team and team.author_id != request.user.id)
        and not (team and team.team_type == Team.TYPE_ADMIN_PRIVATE)
    ):
        team_form = TeamForm(
            instance=team,
            competition=competition,
            user=request.user,
        )

    data['team_form'] = team_form
    data['preview_team_members'] = (
        TeamMember.objects.filter(
            team=team, invitation_status=TeamMember.INVITATION_ACCEPTED
        )
        .select_related('member')
        .order_by('member_name')
    )
    return data


def _handle_registration_post_request(request, competition, data):
    """Returns TeamForm or a redirect action or None."""
    assert request.method == 'POST'
    team = data['team']

    if 'invitation-accept' in request.POST:
        if team:
            return None  # Ignore, team already selected.
        if competition.is_individual_competition:
            return (400, "Invitations only valid for team competitions.")
        team = get_object_or_404(Team, id=request.POST['invitation-accept'])
        team_member = get_object_or_404(TeamMember, team=team, member=request.user)
        team_member.invitation_status = TeamMember.INVITATION_ACCEPTED
        team_member.is_selected = True
        team_member.save()
        TeamMember.objects.filter(
            team__competition=competition, member=request.user
        ).exclude(id=team_member.id).exclude(
            invitation_status=TeamMember.INVITATION_ACCEPTED
        ).delete()
        TeamMember.objects.filter(
            team__competition=competition, member=request.user
        ).exclude(id=team_member.id).update(is_selected=False)
        data['team_invitations'] = []
        return (request.get_full_path(),)  # Prevent form resubmission.

    if 'create-admin-private-team' in request.POST:
        if not data['is_admin']:
            return (400, "admin private teams are available only to admins")
        if data['has_private_team']:
            return None  # Ignore.
        name = request.user.username
        team = Team(
            name=name + " (private)",
            author=request.user,
            competition=competition,
            team_type=Team.TYPE_ADMIN_PRIVATE,
        )
        team.save()
        TeamMember.objects.filter(
            member=request.user, team__competition=competition
        ).update(is_selected=False)
        TeamMember.objects.create(
            team=team,
            member=request.user,
            member_name=name,
            is_selected=True,
            invitation_status=TeamMember.INVITATION_ACCEPTED,
        )
        return (request.get_full_path() + '?created=1',)

    team_form = TeamForm(
        request.POST,
        competition=competition,
        instance=team,
        user=request.user,
    )
    if team_form.is_valid():
        edit = team is not None
        team = team_form.save(commit=False)
        if not edit:
            data['team'] = team
            if data['is_admin']:
                team.team_type = Team.TYPE_UNOFFICIAL
            else:
                team.team_type = Team.TYPE_NORMAL
        team.save()

        _update_team_invitations(team, team_form)

        if not edit:
            TeamMember.objects.filter(
                team__competition=competition, member=request.user
            ).exclude(team=team).delete()
            if competition.is_course:
                return ('competition_registration_complete_course.html', data)
            else:
                return ('competition_registration_complete.html', data)

        # Need to refresh data from the decorator...
        url = request.get_full_path()
        if '?changes=1' not in url:
            url += '?changes=1'
        return (url,)

    return team_form


@competition_view()
@response('competition_rules.html')
def rules(request, competition, data):
    evaluator = get_evaluator(competition.evaluator_version)
    types = evaluator.get_variable_types()
    # Class object is a callable, so wrap it with another function. If the
    # lambda was simply written as "lambda: x", all the values would have the
    # same x.
    data['variable_types'] = [(lambda y=x: y) for x in types]
    data['help_authors_general'] = evaluator.help_authors_general()
    return data


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


def pick_name_translation(name, competition, lang):
    """Pick the correct chain or category name translation.

    Parse a string of form "translation1 | ... | translationN" and pick the
    translation matching the current language. The order of languages is
    defined at the competition level.

    The original string is returned if
        - the current language does not match any competition language, or
        - the number of translations in `name` does not match the number of
          competition languages.
    """
    languages = competition.get_languages()
    try:
        index = languages.index(lang)
    except ValueError:
        return name
    translations = name.split('|')
    if len(translations) != len(languages):
        return name
    return translations[index].strip()


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

    categories, all_chains = _init_categories_and_sort_chains(
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


@competition_view()
@response('competition_task_detail.html')
def task_detail(request, competition, data, ctask_id):
    is_admin = data['is_admin']
    extra = ['task__author'] if is_admin else []
    ctask = get_object_or_404(
        CompetitionTask.objects.select_related(
            'chain', 'task', 'task__content', *extra
        ),
        competition=competition,
        id=ctask_id,
    )

    ctask.competition = competition
    ctask_id = int(ctask_id)
    team = data['team']
    if not is_admin:
        if (
            (not team and not data['has_finished'])
            or not data['has_started']
            or not ctask.chain
            or ctask.chain.unlock_minutes > data['minutes_passed']
            or not ctask.chain.team_has_access(data['team'])
        ):
            raise Http404

    evaluator = get_evaluator(competition.evaluator_version)
    variables = safe_parse_descriptor(evaluator, ctask.descriptor)

    if team:
        ctasks, chain_submissions = load_and_preprocess_chain(
            competition, ctask.chain, team, preloaded_ctask=ctask
        )
        submissions = [x for x in chain_submissions if x.ctask_id == ctask_id]
        submissions.sort(key=lambda x: x.date)

        if data['has_finished']:
            ctask.t_is_locked = False

        if ctask.t_is_locked and not is_admin:
            raise Http404

    if team and ctask.is_automatically_graded():
        if request.method == 'POST' and (not data['has_finished'] or is_admin):
            solution_form = CompetitionSolutionForm(
                request.POST, descriptor=ctask.descriptor, evaluator=evaluator
            )
            new_chain_submissions = None
            if is_admin and 'delete-submission' in request.POST:
                try:
                    submission = Submission.objects.get(
                        id=request.POST['delete-submission']
                    )
                    new_chain_submissions = [
                        x for x in chain_submissions if x != submission
                    ]
                    submissions = [x for x in submissions if x != submission]
                    submission.delete()
                except Submission.DoesNotExist:
                    pass
            elif solution_form.is_valid():
                # TODO: Ignore submission if already correctly solved.
                if len(submissions) < ctask.max_submissions:
                    result = solution_form.cleaned_data['result']
                    is_correct = evaluator.check_result(ctask.descriptor, result)
                    submission = Submission(
                        ctask=ctask,
                        team=team,
                        result=result,
                        score=is_correct * ctask.max_score,
                    )
                    submission.save()
                    new_chain_submissions = chain_submissions + [submission]
                    submissions.append(submission)

            if new_chain_submissions is not None:
                if is_admin and team.is_admin_private():
                    update_ctask_cache_admin_solved_count(
                        competition, ctask, ctask.chain
                    )
                if ctask.chain:
                    update_score_on_ctask_action(
                        competition,
                        team,
                        ctask.chain,
                        chain_ctasks=ctasks,
                        old_chain_submissions=chain_submissions,
                        new_chain_submissions=new_chain_submissions,
                    )

                # Prevent form resubmission.
                return (ctask.get_absolute_url(),)

        else:
            solution_form = CompetitionSolutionForm(
                descriptor=ctask.descriptor, evaluator=evaluator
            )

        data['is_solved'] = any(x.score for x in submissions)
        data['solution_form'] = solution_form
        data['submissions'] = submissions
        data['submissions_left'] = ctask.max_submissions - len(submissions)

    if team and ctask.is_manually_graded():
        if submissions:
            # If it somehow happens that there is more than one submission,
            # consider only the first one.
            submission = submissions[0]
            content = submission.content
        else:
            submission = content = None

        content_form = MathContentForm(request.POST or None, instance=content)
        if (
            request.method == 'POST'
            and (not data['has_finished'] or is_admin)
            and content_form.is_valid()
        ):
            content_form = MathContentForm(request.POST, instance=content)
            content = content_form.save()
            if not submission:
                submission = Submission(
                    ctask=ctask,
                    team=team,
                    content=content,
                    result=settings.COMPETITION_MANUAL_GRADING_TAG,
                )
            submission.mark_unseen_team_activity()
            submission.save()

            # Prevent form resubmission.
            return (ctask.get_absolute_url(),)
        elif (
            submission
            and submission.oldest_unseen_admin_activity
            != Submission.NO_UNSEEN_ACTIVITIES_DATETIME
        ):
            data['unread_newer_than'] = submission.oldest_unseen_admin_activity
            submission.oldest_unseen_admin_activity = (
                Submission.NO_UNSEEN_ACTIVITIES_DATETIME
            )
            submission.save()

        data['content_form'] = content_form
        data['submission'] = submission
        if submission:
            data['submission_actions'], data['not_graded'] = get_submission_actions(
                submission
            )

    if is_admin:
        data['all_ctask_submissions'] = list(
            Submission.objects.filter(ctask_id=ctask_id)
            .select_related('team')
            .order_by('id')
        )
        for submission in data['all_ctask_submissions']:
            submission.team.competition = competition
            submission.ctask = ctask

    data['help_text'] = get_solution_help_text(variables)
    data['chain'] = ctask.chain
    data['ctask'] = ctask

    if (
        competition.show_solutions
        and data['has_finished']
        and not data.get('is_solved', False)
    ):
        data['sample_solution'] = get_sample_solution(variables)

    return data


@competition_view(permission=EDIT)
@response('competition_submission_detail.html')
def submission_detail(request, competition, data, submission_id=None):
    """Competition admin view of a submission for grading purposes."""
    submission = get_object_or_404(
        Submission.objects.select_related('content', 'ctask', 'team'), id=submission_id
    )
    ctask = submission.ctask
    team = submission.team
    if (
        ctask.competition_id != competition.id
        or not ctask.is_manually_graded()
        or submission.content is None
    ):
        raise Http404

    data['submission_actions'], not_graded = get_submission_actions(submission)

    if request.method == 'POST' and 'score_number' in request.POST:
        # TODO: Make a proper form with a custom range widget. For now the
        # interface relies on browser side validation.
        try:
            score = int(request.POST['score_number'])
        except ValueError:
            return (400, "score_number must be an integer")
        if score < 0 or score > ctask.max_score:
            return (400, "score_number must be between 0 and " + str(ctask.max_score))
        if score != submission.score or (score == 0 and not_graded):
            submission.score = score
            submission.mark_unseen_admin_activity()
            submission.reset_unseen_team_activities()
            submission.save()

            # For now, just refresh whole team. A faster solution would be to
            # refresh the score based on chain only.
            refresh_teams_cache_score([team])

            # We need to store a single number, so we hack it into
            # action_object_id and use a fake action_object_content_type_id.
            _action.add(
                request.user,
                _action.COMPETITION_UPDATE_SUBMISSION_SCORE,
                action_object_content_type_id=-1,
                action_object_id=score,
                target=submission,
                fake_action_object=True,
            )

            return (request.get_full_path(),)  # Prevent form resubmission.

    if request.method == 'POST' and 'mark_new' in request.POST:
        as_unread = request.POST['mark_new'] == '1'
        if as_unread:
            submission.mark_unseen_team_activity()
        else:
            submission.reset_unseen_team_activities()
        submission.save()
        return (request.get_full_path(),)  # Prevent form resubmission.

    if (
        submission.oldest_unseen_team_activity
        != Submission.NO_UNSEEN_ACTIVITIES_DATETIME
    ):
        data['unread_newer_than'] = submission.oldest_unseen_team_activity

    data['submission'] = submission
    data['ctask'] = ctask
    data['team'] = team
    return data


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
    categories, chains = _init_categories_and_sort_chains(
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
        # FIXME: Explain why is chain_position 1-based.
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


@competition_view(permission=EDIT)
@response('competition_chain_list.html')
def chain_list(request, competition, data):
    chains = Chain.objects.filter(competition=competition)
    categories, chains = _init_categories_and_sort_chains(
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


def _notification_ctask_prefix(ctask, is_admin):
    task_link = u'[b]{} [url={}]{}[/url][/b]\n\n'.format(
        _("Task:"), ctask.get_absolute_url(), latex_escape(ctask.get_name())
    )
    if is_admin:
        return task_link
    return task_link + '<' + _("Write the question / message here.") + '>'


@competition_view()
@response('competition_notifications.html')
def notifications(request, competition, data, ctask_id=None):
    team = data['team']

    # This could return None as a member, but that's not a problem.
    member_ids = set(
        TeamMember.objects.filter(team=team).values_list('member_id', flat=True)
    )

    posts = list(competition.posts.select_related('author', 'content'))
    if team:
        team_posts = list(team.posts.select_related('author', 'content'))
        for post in team_posts:
            post.t_team = team
        posts += team_posts
        post_form = team.posts.get_post_form()
        if ctask_id is not None:
            ctask = get_object_or_404(
                CompetitionTask.objects.select_related('chain'), id=ctask_id
            )
            ctask.competition = competition
            post_form.fields['text'].initial = _notification_ctask_prefix(
                ctask, data['is_admin']
            )
        data['post_form'] = post_form

    posts.sort(key=lambda post: post.date_created, reverse=True)

    data['posts'] = posts
    data['target_container'] = team
    data['team_member_ids'] = member_ids
    return data


@competition_view(permission=EDIT)
@response('competition_notifications_admin.html')
def notifications_admin(request, competition, data):
    team_ct = ContentType.objects.get_for_model(Team)
    teams = Team.objects.filter(competition=competition)
    team_ids_query = teams.values_list('id', flat=True)

    if request.method == 'POST':
        # Handle post hide/show (mark as answered/unanswered).
        # We use `extra == 0` as unanswered, `extra == 1` as answered.
        action = request.POST.get('action', '')
        match = re.match(r'(show|hide)-(\d+)', action)
        if match:
            post_id = int(match.group(2))
            extra = 1 if match.group(1) == 'hide' else 0

            # Update if competition-related post.
            competition.posts.filter(id=post_id).update(extra=extra)

            # Update if team-related post. As noted below, using
            # `team__competition_id` makes one JOIN too much.
            Post.objects.filter(
                id=post_id, content_type=team_ct, object_id__in=team_ids_query
            ).update(extra=extra)

    show_answered = request.GET.get('answered') == '1'
    extra_filter = {} if show_answered else {'extra': 0}

    posts = list(
        competition.posts.filter(**extra_filter).select_related('author', 'content')
    )
    teams = list(teams)
    teams_dict = {x.id: x for x in teams}
    # Post.objects.filter(team__competition_id=id, ct=...) makes an extra JOIN.
    team_posts = list(
        Post.objects.filter(
            content_type=team_ct, object_id__in=team_ids_query, **extra_filter
        ).select_related('author', 'content')
    )
    user_ids = [post.author_id for post in team_posts]
    user_id_to_team = get_teams_for_user_ids(competition, user_ids)
    for post in team_posts:
        post.t_team = user_id_to_team.get(post.author_id)
        if post.t_team:
            post.t_team.competition = competition
        post.t_target_team = teams_dict.get(post.object_id)
        if post.t_target_team:
            post.t_target_team.competition = competition

    post_form = PostsForm(placeholder=_("Message"))
    if 'ctask' in request.GET:
        try:
            ctask = CompetitionTask.objects.get(
                competition=competition, id=request.GET['ctask']
            )
        except CompetitionTask.DoesNotExist:
            pass
        else:
            post_form.fields['text'].initial = _notification_ctask_prefix(
                ctask, data['is_admin']
            )
    if 'team' in request.GET:
        try:
            selected_team_id = int(request.GET['team'])
        except ValueError:
            pass
        else:
            for team in teams:
                if team.id == selected_team_id:
                    data['selected_team_id'] = selected_team_id
                    team.t_selected_attr = ' selected="selected"'
                    break
    if 'ctask' in request.GET or 'team' in request.GET:
        post_form.fields['text'].widget.attrs['autofocus'] = 'autofocus'

    posts += team_posts
    posts.sort(key=lambda post: post.date_created, reverse=True)

    data.update(
        {
            'competition_ct': ContentType.objects.get_for_model(Competition),
            'post_form': post_form,
            'posts': posts,
            'show_answered': show_answered,
            'team_ct': team_ct,
            'teams': teams,
        }
    )
    return data
