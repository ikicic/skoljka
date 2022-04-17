from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.forms.models import modelformset_factory
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _, ungettext

from mathcontent.forms import MathContentForm
from mathcontent.latex import latex_escape
from mathcontent.models import MathContent
from permissions.constants import VIEW, EDIT
from permissions.models import ObjectPermission
from post.forms import PostsForm
from post.models import Post
from skoljka.libs.decorators import response
from tags.utils import add_tags
from task.models import Task
from userprofile.forms import AuthenticationFormEx

from competition.decorators import competition_view
from competition.evaluator import get_evaluator, get_solution_help_text, \
        get_sample_solution, safe_parse_descriptor
from competition.forms import ChainForm, \
        ChainTasksForm, clean_unused_ctask_ids, \
        CompetitionSolutionForm, CompetitionTaskForm, \
        BaseCompetitionTaskFormSet, TeamForm, TaskListAdminPanelForm
from competition.models import Chain, Competition, CompetitionTask, Team, \
        TeamMember, Submission
from competition.utils import update_chain_comments_cache, \
        comp_url, update_score_on_ctask_action, preprocess_chain, \
        get_teams_for_user_ids, lock_ctasks_in_chain, \
        refresh_teams_cache_score, update_ctask_task, \
        is_ctask_comment_important, ctask_comment_verified_class, \
        detach_ctask_from_chain, delete_chain, \
        refresh_chain_cache_is_verified, \
        update_chain_cache_is_verified, \
        refresh_ctask_cache_admin_solved_count, \
        update_ctask_cache_admin_solved_count, \
        update_chain_ctasks, parse_team_categories, \
        refresh_submissions_cache_is_correct

from skoljka.libs.decorators import require

from collections import defaultdict
from datetime import datetime
import django_sorting

import re

#TODO: Option for admins to create a team even if they have a private group.
#TODO: When updating chain_position, update task name.
#TODO: Formalize when update_ does .save() or not.

@response('competition_list.html')
def competition_list(request):
    competitions = Competition.objects \
            .for_user(request.user, VIEW).distinct().order_by('-start_date')
    member_of = list(TeamMember.objects \
        .filter(member_id=request.user.id,
            invitation_status=TeamMember.INVITATION_ACCEPTED) \
        .values_list('team__competition_id', flat=True))

    return {'competitions': competitions, 'current_time': datetime.now(),
            'member_of': member_of}


@competition_view()
@response('competition_homepage.html')
def homepage(request, competition, data):
    return data


def _update_team_invitations(team, team_form):
    old_invitations = list(TeamMember.objects.filter(team=team))
    old_invitations_dict = \
            {x.member_id: x for x in old_invitations if x.member_id}

    author = team.author
    members = team_form._members
    members.append((author.username, author)) # Author is also a member
    new_invited_users_ids = set(user.id for name, user in members if user)

    # Delete old invitations (keep old TeamMember instances if necessary).
    for invitation in old_invitations:
        if invitation.member_id is None \
                or invitation.member_id not in new_invited_users_ids:
            invitation.delete()

    # Insert new invitations (don't duplicate TeamMember).
    for name, user in members:
        if not user or user.id not in old_invitations_dict:
            status = TeamMember.INVITATION_ACCEPTED \
                    if not user or user.id == author.id \
                    else TeamMember.INVITATION_UNANSWERED
            TeamMember.objects.create(team=team, member=user, member_name=name,
                    invitation_status=status)


@competition_view()
@response('competition_team_detail.html')
def team_detail(request, competition, data, team_id):
    data['preview_team'] = \
            get_object_or_404(Team, id=team_id, competition_id=competition.id)
    data['preview_team_members'] = TeamMember.objects.filter(team_id=team_id,
            invitation_status=TeamMember.INVITATION_ACCEPTED) \
                    .select_related('member')
    if data['is_admin']:
        data['submissions'] = list(Submission.objects \
                .filter(team_id=team_id) \
                .select_related('ctask', 'ctask__chain__name') \
                .order_by('id'))
        for submission in data['submissions']:
            if submission.ctask.chain_id:
                submission.ctask.chain.competition = competition
            submission.ctask.competition = competition
    return data


@competition_view()
@response('competition_registration.html')
def registration(request, competition, data):
    if data['has_finished']:
        return (competition.get_absolute_url(), )
    if competition.registration_open_date > data['current_time'] and \
            not data['is_admin']:
        return (competition.get_absolute_url(), )
    if not request.user.is_authenticated():
        data['form'] = AuthenticationFormEx()
        return 'competition_registration_login.html', data

    team = data['team']
    edit = team is not None
    team_form = None
    is_course = competition.is_course

    if team and is_course:
        return (competition.get_absolute_url(), )

    if not team and request.method == 'POST' \
            and not is_course \
            and 'invitation-accept' in request.POST:
        team = get_object_or_404(Team, id=request.POST['invitation-accept'])
        team_member = get_object_or_404(TeamMember, team=team,
                member=request.user)
        team_member.invitation_status = TeamMember.INVITATION_ACCEPTED
        team_member.is_selected = True
        team_member.save()
        TeamMember.objects \
                .filter(team__competition=competition, member=request.user) \
                .exclude(id=team_member.id) \
                .exclude(invitation_status=TeamMember.INVITATION_ACCEPTED) \
                .delete()
        TeamMember.objects \
                .filter(team__competition=competition, member=request.user) \
                .exclude(id=team_member.id) \
                .update(is_selected=False)
        data['team'] = team
        data['team_invitations'] = []
    elif request.method == 'POST' \
            and 'name' in request.POST \
            and not is_course:
        team_form = TeamForm(request.POST, competition=competition,
                max_team_size=competition.max_team_size, instance=team,
                user=request.user)
        if team_form.is_valid():
            old_team = team
            team = team_form.save(commit=False)
            if not edit:
                team.competition = competition
                team.author = request.user
                if data['is_admin']:
                    team.team_type = Team.TYPE_UNOFFICIAL
                else:
                    team.team_type = Team.TYPE_NORMAL
            team.save()

            _update_team_invitations(team, team_form)

            if not old_team:
                TeamMember.objects \
                        .filter(team__competition=competition,
                                member=request.user) \
                        .exclude(team=team).delete()
                data['team'] = team
                return ('competition_registration_complete.html', data)
            # Need to refresh data from the decorator...
            url = request.get_full_path()
            if '?changes=1' not in url:
                url += '?changes=1'
            return (url, )
    elif request.method == 'POST' and data['is_admin'] \
            and 'create-admin-private-team' in request.POST \
            and not data['has_private_team']:
        name = request.user.username
        team = Team(name=name + " (private)",
                author=request.user, competition=competition,
                team_type=Team.TYPE_ADMIN_PRIVATE)
        team.save()
        TeamMember.objects.filter(member=request.user,
                team__competition=competition).update(is_selected=False)
        TeamMember.objects.create(team=team, member=request.user,
                member_name=name, is_selected=True,
                invitation_status=TeamMember.INVITATION_ACCEPTED)
        return (request.get_full_path() + '?created=1', )
    elif request.method == 'POST' and is_course:
        assert not team
        name = request.user.username
        team = Team(name=name, author=request.user, competition=competition,
                    team_type=Team.TYPE_NORMAL)
        team.save()
        TeamMember.objects.create(
                team=team, member=request.user, member_name=name,
                is_selected=True,
                invitation_status=TeamMember.INVITATION_ACCEPTED)
        data['team'] = team
        return ('competition_registration_complete_course.html', data)


    if team_form is None \
            and not (team and team.author_id != request.user.id) \
            and not (team and team.team_type == Team.TYPE_ADMIN_PRIVATE):
        team_form = TeamForm(instance=team, competition=competition,
                max_team_size=competition.max_team_size, user=request.user)

    data['team_form'] = team_form
    data['preview_team_members'] = TeamMember.objects.filter(
                team=team, invitation_status=TeamMember.INVITATION_ACCEPTED) \
            .select_related('member')
    return data


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
def scoreboard(request, competition, data):
    if data['is_admin'] and 'refresh' in request.POST:
        start = datetime.now()
        teams = Team.objects.filter(competition=data['competition'])
        refresh_teams_cache_score(teams)
        data['refresh_calculation_time'] = datetime.now() - start

    extra = {} if data['is_admin'] else {'team_type': Team.TYPE_NORMAL}
    sort_by_actual_score = data['is_admin'] and \
            request.GET.get('sort_by_actual_score') == '1'
    order_by = '-cache_score' if sort_by_actual_score \
            else '-cache_score_before_freeze'
    teams = list(Team.objects.filter(competition=competition, **extra) \
            .order_by(order_by, 'id') \
            .only('id', 'name', 'cache_score', 'cache_score_before_freeze',
                  'cache_max_score_after_freeze', 'team_type', 'category'))

    try:
        team_categories = parse_team_categories(
                competition.team_categories, request.LANGUAGE_CODE)
    except ValueError:
        team_categories = []
    team_categories_dict = dict(team_categories)
    data['team_categories_title'] = u", ".join(team_categories_dict.values())

    last_score = -1
    last_position = 1
    position = 1
    for team in teams:
        team.competition = competition
        if team.is_normal() and team.cache_score_before_freeze != last_score:
            last_position = position
        team.t_position = last_position
        if team_categories:
            team.t_category = team_categories_dict.get(team.category,
                                                       team_categories[-1][1])
        if team.is_normal():
            last_score = team.cache_score_before_freeze
            position += 1

    data['teams'] = teams
    data['sort_by_actual_score'] = sort_by_actual_score
    return data


def pick_chain_name_translation(name, competition, lang):
    """Pick the correct chain name translation.

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
    all_ctasks = list(CompetitionTask.objects.filter(competition=competition))
    all_ctasks_dict = {ctask.id: ctask for ctask in all_ctasks}
    all_chains = list(Chain.objects \
            .filter(competition=competition, cache_is_verified=True) \
            .order_by('category', 'position', 'name'))
    all_chains_dict = {chain.id: chain for chain in all_chains}

    unverified_chains = set()

    for chain in all_chains:
        chain.ctasks = []
        chain.competition = competition # use preloaded object

    for ctask in all_ctasks:
        ctask.competition = competition # use preloaded object
        ctask.t_submission_count = 0
        ctask.t_is_solved = False
        if ctask.score > 1:
            ctask.t_link_text = ctask.score
            ctask.t_title = ungettext(
                    "This task is worth %d point.",
                    "This task is worth %d points.",
                    ctask.score) % ctask.score
        if ctask.chain_id in all_chains_dict:
            chain = all_chains_dict[ctask.chain_id]
            ctask.chain = chain
            chain.ctasks.append(ctask)
        elif ctask.chain_id is not None:
            unverified_chains.add(ctask.chain_id)

    all_my_submissions = list(Submission.objects.filter(team=data['team']) \
            .values_list('ctask_id', 'cache_is_correct'))
    for ctask_id, is_correct in all_my_submissions:
        ctask = all_ctasks_dict[ctask_id]
        ctask.t_submission_count += 1
        ctask.t_is_solved |= is_correct

    category_translations = competition.get_task_categories_translations(
            request.LANGUAGE_CODE)

    class Category(object):
        def __init__(self, name):
            self.name = name
            self.translated_name = category_translations.get(name, name)
            self.chains = []
            self.t_is_hidden = None

    categories = {}
    for chain in all_chains:
        chain.t_is_hidden = data['minutes_passed'] < chain.unlock_minutes

        if not chain.t_is_hidden or data['is_admin']:
            if chain.category not in categories:
                categories[chain.category] = Category(chain.category)
            categories[chain.category].chains.append(chain)

        chain.ctasks.sort(key=lambda ctask: (ctask.chain_position, ctask.id))
        if not data['has_finished']:
            lock_ctasks_in_chain(chain.ctasks)
        else:
            for ctask in chain.ctasks:
                ctask.t_is_locked = False

        chain.t_next_task = None
        for ctask in chain.ctasks:
            if not ctask.t_is_locked and not ctask.t_is_solved and \
                    ctask.t_submission_count < ctask.max_submissions:
                chain.t_next_task = ctask
                break

    if data['is_admin']:
        data['admin_panel_form'] = TaskListAdminPanelForm()
        for category in categories.itervalues():
            category.t_is_hidden = \
                    all(chain.t_is_hidden for chain in category.chains)

    for chain in all_chains:
        chain.t_translated_name = pick_chain_name_translation(
                chain.name, competition, request.LANGUAGE_CODE)

    data['unverified_chains_count'] = len(unverified_chains)
    data['categories'] = sorted(categories.values(), key=lambda x: x.name)
    data['max_chain_length'] = 0 if not all_chains \
            else max(len(chain.ctasks) for chain in all_chains)
    return data


@competition_view()
@response('competition_task_detail.html')
def task_detail(request, competition, data, ctask_id):
    is_admin = data['is_admin']
    extra = ['task__author'] if is_admin else []
    ctask = get_object_or_404(
            CompetitionTask.objects.select_related('chain', 'task',
                'task__content', *extra),
            competition=competition, id=ctask_id)
    ctask_id = int(ctask_id)
    team = data['team']
    if not is_admin:
        if (not team and not data['has_finished']) or not data['has_started'] \
                or ctask.chain.unlock_minutes > data['minutes_passed']:
            raise Http404

    if ctask.score > 1:
        ctask.t_score_text = ungettext(
                "This task is worth %d point.",
                "This task is worth %d points.",
                ctask.score) % ctask.score

    evaluator = get_evaluator(competition.evaluator_version)
    variables = safe_parse_descriptor(evaluator, ctask.descriptor)

    if team:
        ctasks, chain_submissions = preprocess_chain(
                competition, ctask.chain, team, preloaded_ctask=ctask)
        submissions = [x for x in chain_submissions if x.ctask_id == ctask_id]
        submissions.sort(key=lambda x: x.date)

        if data['has_finished']:
            ctask.t_is_locked = False

        if ctask.t_is_locked and not is_admin:
            raise Http404

    if team and ctask.is_automatically_graded():
        if request.method == 'POST' and (not data['has_finished'] or is_admin):
            solution_form = CompetitionSolutionForm(request.POST,
                    descriptor=ctask.descriptor, evaluator=evaluator)
            submission = None
            delete = False
            if is_admin and 'delete-submission' in request.POST:
                try:
                    submission = Submission.objects.get(
                            id=request.POST['delete-submission'])
                    chain_submissions = \
                            [x for x in chain_submissions if x != submission]
                    submissions = [x for x in submissions if x != submission]
                    submission.delete()
                    delete = True
                except Submission.DoesNotExist:
                    pass
            elif solution_form.is_valid():
                # TODO: Ignore submission if already correctly solved.
                if len(submissions) < ctask.max_submissions:
                    result = solution_form.cleaned_data['result']
                    is_correct = evaluator.check_result(
                            ctask.descriptor, result)
                    submission = Submission(ctask=ctask, team=team,
                            result=result, cache_is_correct=is_correct)
                    submission.save()
                    chain_submissions.append(submission)
                    submissions.append(submission)

            if delete or submission:
                if is_admin and team.is_admin_private():
                    update_ctask_cache_admin_solved_count(
                            competition, ctask, ctask.chain)
                update_score_on_ctask_action(competition, team, ctask.chain,
                        ctask, submission, delete,
                        chain_ctask_ids=[x.id for x in ctasks],
                        chain_submissions=chain_submissions)

                # Prevent form resubmission.
                return (ctask.get_absolute_url(), )

        else:
            solution_form = CompetitionSolutionForm(
                    descriptor=ctask.descriptor, evaluator=evaluator)

        data['is_solved'] = any(x.cache_is_correct for x in submissions)
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
        if request.method == 'POST' \
                and (not data['has_finished'] or is_admin) \
                and content_form.is_valid():
            content_form = MathContentForm(request.POST, instance=content)
            content = content_form.save()
            if not submission:
                submission = Submission(
                        ctask=ctask, team=team, content=content,
                        result=settings.COMPETITION_MANUAL_GRADING_TAG,
                        cache_is_correct=False)
                submission.save()

            # Prevent form resubmission.
            return (ctask.get_absolute_url(), )

        data['content_form'] = content_form
        data['submission'] = submission

    if is_admin:
        data['all_ctask_submissions'] = list(Submission.objects \
                .filter(ctask_id=ctask_id) \
                .select_related('team') \
                .order_by('id'))
        for submission in data['all_ctask_submissions']:
            submission.team.competition = competition

    data['help_text'] = get_solution_help_text(variables)
    data['chain'] = ctask.chain
    data['ctask'] = ctask

    if competition.show_solutions and data['has_finished'] \
            and not data.get('is_solved', False):
        data['sample_solution'] = get_sample_solution(variables)

    return data



@competition_view(permission=EDIT)
@response('competition_task_new.html')
def task_new(request, competition, data, ctask_id=None):
    if ctask_id:
        ctask = get_object_or_404(
                CompetitionTask.objects.select_related('task'),
                id=ctask_id, competition_id=competition.id)
        edit = True
    else:
        ctask = None
        edit = False

    POST = request.POST if request.method == 'POST' else None
    form = CompetitionTaskForm(POST, instance=ctask, competition=competition,
            user=request.user)

    if request.method == 'POST' and form.is_valid():
        ctask = form.save(commit=False)
        if not edit:
            ctask.competition = competition
            ctask.chain = None
            ctask.chain_position = -1
            ctask.max_submissions = competition.default_max_submissions

        _create_or_update_task(ctask, request.user, competition,
                ctask.chain, ctask.chain_position, ctask._text,
                ctask._comment)

        ctask.save()

        if ctask.chain:
            chain_ctasks = CompetitionTask.objects.filter(chain=ctask.chain) \
                    .select_related('comment').only('id', 'comment')
            update_chain_comments_cache(ctask.chain, chain_ctasks)
            update_chain_cache_is_verified(competition, ctask.chain)
            ctask.chain.save()

        target = request.POST.get('next', 'stay')
        if target == 'next':
            return (comp_url(competition, 'task/new'), )
        if target == 'tasks':
            return (comp_url(competition, 'chain/tasks'), )
        return (ctask.get_edit_url(), )  # stay

    data['is_solution_hidden'] = \
            ctask and ctask.task.author_id != request.user.id
    data['form'] = form
    data['ctask'] = ctask
    return data



@competition_view(permission=EDIT)
@response('competition_chain_list_tasks.html')
def chain_tasks_list(request, competition, data):
    created = False
    updated_chains_count = None
    updated_ctasks_count = None
    updated_submissions_cache_is_correct = None
    empty_form = ChainTasksForm(competition=competition)
    form = empty_form

    if request.POST.get('action') == 'refresh-chain-cache-is-verified':
        updated_chains_count = len(refresh_chain_cache_is_verified(competition))
    elif request.POST.get('action') == 'refresh-ctask-cache-admin-solved-count':
        updated_ctasks_count = len(
                refresh_ctask_cache_admin_solved_count(competition))
    elif request.POST.get('action') == 'refresh-submission-cache-is-correct':
        updated_submissions_cache_is_correct = \
                refresh_submissions_cache_is_correct(competitions=[competition])
    elif request.method == 'POST':
        form = ChainTasksForm(request.POST, competition=competition)
        if form.is_valid():
            chain = form.save(commit=False)
            chain.competition = competition
            chain.save()

            old_ids = CompetitionTask.objects \
                    .filter(chain=chain).values_list('id', flat=True)
            new_ids = [x.id for x in form.cleaned_data['ctasks']]
            update_chain_ctasks(competition, chain, old_ids, new_ids)
            created = True
            form = empty_form  # Empty the form.

    chains = Chain.objects.filter(competition=competition)
    order_by_field = django_sorting.middleware.get_field(request)
    if len(order_by_field) > 1:
        chains = chains.order_by(order_by_field, 'category', 'position', 'name')
    else:
        chains = chains.order_by('category', 'position', 'name')

    chain_dict = {chain.id: chain for chain in chains}
    ctasks = list(CompetitionTask.objects.filter(competition=competition) \
            .select_related('task__author', 'task__content__text',
                'comment__text'))
    ctask_dict = {ctask.id: ctask for ctask in ctasks}

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
        is_important = ctask.comment.text.strip() and \
                is_ctask_comment_important(ctask.comment.text)
        ctask.t_class = ctask_comment_verified_class(
                competition, ctask, request.user, is_important=is_important)

    for chain in chains:
        chain.t_ctasks.sort(key=lambda x: x.chain_position)
        chain.t_class = \
                'cchain-verified-list' if chain.cache_is_verified else ''

    data['created'] = created
    data['form'] = form
    data['chains'] = chains
    data['unused_ctasks'] = unused_ctasks
    data['trans_checked_title'] = _("Number of admins that solved this task.")
    data['updated_chains_count'] = updated_chains_count
    data['updated_ctasks_count'] = updated_ctasks_count
    data['updated_submissions_cache_is_correct'] = \
            updated_submissions_cache_is_correct
    return data


@require(post=['action'])
@competition_view(permission=EDIT)
@response()
def chain_tasks_action(request, competition, data):
    action = request.POST['action']
    url_suffix = ""
    if re.match('delete-chain-(\d+)', action):
        # Delete whole chain. Does not delete ctasks, of course.
        id = int(action[len('delete-chain-'):])
        chain = get_object_or_404(Chain, id=id, competition=competition)
        delete_chain(chain)
    elif re.match('detach-(\d+)', action):
        # Detach ctask from a chain.
        id = int(action[len('detach-'):])
        ctask = get_object_or_404(CompetitionTask,
            id=id, competition=competition)
        url_suffix = '#chain-{}'.format(ctask.chain_id)
        detach_ctask_from_chain(ctask)
    elif action == 'add-after':
        # Add tasks at the beginning of a chain or after a given ctask.
        try:
            ctask_ids = request.POST['ctask-ids']
            after_what = request.POST['after-what']
            after_id = request.POST['after-id']
        except KeyError as e:
            return (400, "POST arguments missing " + e.message)
        if after_what == 'chain':
            chain = get_object_or_404(
                    Chain, id=after_id, competition=competition)
            position = 0
        elif after_what == 'ctask':
            ctask = get_object_or_404(
                    CompetitionTask.objects.select_related('chain'),
                    id=after_id, competition=competition)
            chain = ctask.chain
            position = ctask.chain_position - 1
        else:
            return (400, "after_what={}?".format(after_what))
        old_ids = list(CompetitionTask.objects.filter(chain=chain) \
                .order_by('chain_position').values_list('id', flat=True))
        try:
            selected_ids, selected_ctasks = clean_unused_ctask_ids(
                    competition, ctask_ids)
        except ValidationError:
            return (400, "invalid ctask_ids: {}".format(ctask_ids))

        new_ids = old_ids[:position] + selected_ids + old_ids[position:]
        update_chain_ctasks(competition, chain, old_ids, new_ids)
        url_suffix = '#chain-{}'.format(chain.id)
    elif re.match('move-(lo|hi)-(\d+)', action):
        id = int(action[len('move-lo-'):])
        ctask = get_object_or_404(
                CompetitionTask.objects.select_related('chain'),
                id=id, competition=competition)
        old_ids = list(CompetitionTask.objects.filter(chain=ctask.chain) \
                .order_by('chain_position').values_list('id', flat=True))
        pos = ctask.chain_position - 1
        new_ids = old_ids[:]
        if action[5] == 'l' and pos > 0:
            new_ids[pos], new_ids[pos - 1] = new_ids[pos - 1], new_ids[pos]
        elif action[5] == 'h' and pos < len(old_ids) - 1:
            new_ids[pos], new_ids[pos + 1] = new_ids[pos + 1], new_ids[pos]

        url_suffix = '#chain-{}'.format(ctask.chain.id)
        update_chain_ctasks(competition, ctask.chain, old_ids, new_ids)
    else:
        return (400, "Unrecognized action " + action)
    return (comp_url(competition, "chain/tasks") + url_suffix, )



@competition_view(permission=EDIT)
@response('competition_chain_list.html')
def chain_list(request, competition, data):
    chains = Chain.objects.filter(competition=competition)
    order_by_field = django_sorting.middleware.get_field(request)
    if len(order_by_field) > 1:
        chains = chains.order_by(order_by_field, 'category', 'position', 'name')
    else:
        chains = chains.order_by('category', 'position', 'name')
    chain_dict = {chain.id: chain for chain in chains}
    ctasks = list(CompetitionTask.objects.filter(competition=competition) \
            .values_list('id', 'chain_id', 'task__author_id'))
    author_ids = [author_id for ctask_id, chain_id, author_id in ctasks]
    authors = User.objects.only('id', 'username', 'first_name', 'last_name') \
            .in_bulk(set(author_ids))

    verified_ctask_ids = set(Submission.objects \
            .filter(team__competition_id=competition.id,
                    team__team_type=Team.TYPE_ADMIN_PRIVATE,
                    cache_is_correct=True) \
            .values_list('ctask_id', flat=True))

    for chain in chains:
        chain.competition = competition
        chain.t_ctask_count = 0
        chain._author_ids = set()
        chain.t_is_verified = True

    for ctask_id, chain_id, author_id in ctasks:
        if chain_id is None:
            continue
        chain = chain_dict[chain_id]
        chain.t_ctask_count += 1
        chain._author_ids.add(author_id)
        if ctask_id not in verified_ctask_ids:
            chain.t_is_verified = False

    from userprofile.templatetags.userprofile_tags import userlink
    for chain in chains:
        chain.t_authors = mark_safe(u", ".join(userlink(authors[author_id])
                for author_id in chain._author_ids))

    data['chains'] = chains
    return data


def _create_or_update_task(
        ctask, user, competition, chain, index, text, comment):
    edit = bool(ctask.task_id)
    if not edit:
        content = MathContent(text=text)
        content.save()
        task = Task(content=content, author=user, hidden=True)
        comment = MathContent(text=comment)
        comment.save()
        ctask.comment = comment
    else:
        task = ctask.task
        task.content.text = text
        task.content.save()
        ctask.comment.text = comment
        ctask.comment.save()

    update_ctask_task(task, competition, chain, index + 1, commit=True)

    if not edit:
        if competition.automatic_task_tags:
            add_tags(task, competition.automatic_task_tags)
        if competition.admin_group:
            ObjectPermission.objects.create(content_object=task,
                    group=competition.admin_group, permission_type=VIEW)
            ObjectPermission.objects.create(content_object=task,
                    group=competition.admin_group, permission_type=EDIT)
        ctask.task = task


@competition_view(permission=EDIT)
@response('competition_chain_overview.html')
def chain_overview(request, competition, data, chain_id):
    chain = get_object_or_404(Chain, id=chain_id, competition_id=competition.id)
    chain.competition = competition
    ctasks = CompetitionTask.objects.filter(chain=chain) \
            .select_related('task__content', 'task__author', 'comment') \
            .order_by('chain_position')
    for ctask in ctasks:
        ctask.competition = competition

    data['chain'] = chain
    data['ctasks'] = ctasks
    return data


@competition_view(permission=EDIT)
@response('competition_chain_new.html')
def chain_new(request, competition, data, chain_id=None):
    if chain_id:
        chain = get_object_or_404(
                Chain, id=chain_id, competition_id=competition.id)
        edit = True
    else:
        chain = None
        edit = False

    POST = request.POST if request.method == 'POST' else None
    chain_form = ChainForm(POST, competition=competition, instance=chain)

    if request.method == 'POST':
        if chain_form.is_valid():
            chain = chain_form.save(commit=False)
            if not edit:
                chain.competition = competition
            chain.save()

            return (chain.get_absolute_url(), )

    data['chain_form'] = chain_form
    return data


def chain_edit(request, competition_id, chain_id):
    return chain_new(request, competition_id, chain_id=chain_id)


def _notification_ctask_prefix(ctask, is_admin):
    task_link = u'[b]{} [url={}]{}[/url][/b]\n\n'.format(
            _("Task:"), ctask.get_absolute_url(),
            latex_escape(ctask.get_name()))
    if is_admin:
        return task_link
    return task_link + '<' + _("Write the question / message here.") + '>'


@competition_view()
@response('competition_notifications.html')
def notifications(request, competition, data, ctask_id=None):
    team = data['team']

    # This could return None as a member, but that's not a problem.
    member_ids = set(TeamMember.objects.filter(team=team) \
            .values_list('member_id', flat=True))

    posts = list(competition.posts.select_related('author', 'content'))
    if team:
        team_posts = list(team.posts.select_related('author', 'content'))
        for post in team_posts:
            post.t_team = team
        posts += team_posts
        post_form = team.posts.get_post_form()
        if ctask_id is not None:
            ctask = get_object_or_404(
                    CompetitionTask.objects.select_related('chain'),
                    id=ctask_id)
            ctask.competition = competition
            post_form.fields['text'].initial = \
                    _notification_ctask_prefix(ctask, data['is_admin'])
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
            Post.objects \
                .filter(id=post_id, content_type=team_ct,
                        object_id__in=team_ids_query) \
                .update(extra=extra)

    show_answered = request.GET.get('answered') == '1'
    extra_filter = {} if show_answered else {'extra': 0}

    posts = list(competition.posts.filter(**extra_filter) \
                            .select_related('author', 'content'))
    teams = list(teams)
    teams_dict = {x.id: x for x in teams}
    # Post.objects.filter(team__competition_id=id, ct=...) makes an extra JOIN.
    team_posts = list(Post.objects \
            .filter(content_type=team_ct, object_id__in=team_ids_query,
                    **extra_filter) \
            .select_related('author', 'content'))
    user_id_to_team = \
            get_teams_for_user_ids([post.author_id for post in team_posts])
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
                    competition=competition, id=request.GET['ctask'])
        except CompetitionTask.DoesNotExist:
            pass
        else:
            post_form.fields['text'].initial = \
                    _notification_ctask_prefix(ctask, data['is_admin'])
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

    data.update({
        'competition_ct': ContentType.objects.get_for_model(Competition),
        'post_form': post_form,
        'posts': posts,
        'show_answered': show_answered,
        'team_ct': team_ct,
        'teams': teams,
    })
    return data
