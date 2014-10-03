from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.forms.models import modelformset_factory
from django.http import Http404
from django.shortcuts import get_object_or_404

from mathcontent.models import MathContent
from permissions.constants import VIEW, EDIT
from permissions.models import ObjectPermission
from post.forms import PostsForm
from post.models import Post
from skoljka.libs.decorators import response
from tags.utils import add_task_tags
from task.models import Task

from competition.decorators import competition_view
from competition.forms import ChainForm, CompetitionTask, \
        BaseCompetitionTaskFormSet, TeamForm
from competition.models import Chain, Competition, CompetitionTask, Team, \
        TeamMember, Submission
from competition.utils import check_single_chain, get_teams_for_user_ids, \
        lock_ctasks_in_chain

from datetime import datetime

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


@login_required
@competition_view()
@response('competition_registration.html')
def registration(request, competition, data):
    team = data.get('team', None)
    edit = team is not None
    team_form = None


    if not team and request.method == 'POST' \
            and 'invitation-accept' in request.POST:
        team = get_object_or_404(Team, id=request.POST['invitation-accept'])
        team_member = get_object_or_404(TeamMember, team=team,
                member=request.user)
        team_member.invitation_status = TeamMember.INVITATION_ACCEPTED
        team_member.save()
        data['team'] = team
        data['team_invitations'] = []

    elif request.method == 'POST' and 'name' in request.POST:
        team_form = TeamForm(request.POST, instance=team,
                max_team_size=competition.max_team_size)
        if team_form.is_valid():
            team = team_form.save(commit=False)
            if not edit:
                team.competition = competition
                team.author = request.user
                if data['is_admin']:
                    team.is_test = True
            team.save()

            _update_team_invitations(team, team_form)

    if team_form is None and (not team or team.author_id == request.user.id):
        team_form = TeamForm(instance=team,
                max_team_size=competition.max_team_size)

    data.update({
        'team_form': team_form,
    })
    return data


@competition_view()
@response('competition_rules.html')
def rules(request, competition, data):
    return data


@login_required
@competition_view()
@response('competition_scoreboard.html')
def scoreboard(request, competition, data):
    teams = list(Team.objects.filter(competition=competition) \
            .order_by('-cache_score') \
            .only('id', 'name', 'cache_score', 'is_test'))

    last_score = -1
    last_position = 1
    position = 1
    for team in teams:
        if not team.is_test and team.cache_score != last_score:
            last_position = position
        team.t_position = last_position
        if not team.is_test:
            last_score = team.cache_score
            position += 1

    data['teams'] = teams
    return data


@competition_view()
@response('competition_task_list.html')
def task_list(request, competition, data):
    all_ctasks = list(CompetitionTask.objects.filter(competition=competition) \
            .select_related('task__content'))
    all_ctasks_dict = {ctask.id: ctask for ctask in all_ctasks}
    all_chains = list(Chain.objects.filter(competition=competition))
    all_chains_dict = {chain.id: chain for chain in all_chains}

    for chain in all_chains:
        chain.ctasks = []
        chain.competition = competition # use preloaded object

    for ctask in all_ctasks:
        chain = all_chains_dict[ctask.chain_id]
        ctask.competition = competition # use preloaded object
        ctask.chain = chain
        ctask.t_submission_count = 0
        ctask.t_is_solved = False
        chain.ctasks.append(ctask)

    all_my_submissions = list(Submission.objects.filter(team=data['team']) \
            .values_list('ctask_id', 'cache_is_correct'))
    for ctask_id, is_correct in all_my_submissions:
        ctask = all_ctasks_dict[ctask_id]
        ctask.t_submission_count += 1
        ctask.t_is_solved |= is_correct


    class Category(object):
        def __init__(self, name):
            self.name = name
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
        lock_ctasks_in_chain(chain.ctasks)

    if data['is_admin']:
        for category in categories.itervalues():
            category.t_is_hidden = \
                    all(chain.t_is_hidden for chain in category.chains)

    data['categories'] = categories
    data['max_chain_length'] = max(len(chain.ctasks) for chain in all_chains)
    return data


@competition_view()
@response('competition_task_detail.html')
def task_detail(request, competition, data, ctask_id):
    ctask = get_object_or_404(
            CompetitionTask.objects.select_related('chain', 'task',
                'task__content'),
            competition=competition, id=ctask_id)
    team = data['team']
    if not data['is_admin']:
        if not team or not data['has_started'] \
                or ctask.chain.unlock_minutes > data['minutes_passed']:
            raise Http404

    if team:
        submissions = list(Submission.objects \
                .filter(ctask=ctask, team=team) \
                .order_by('date') \
                .only('id', 'result', 'cache_is_correct'))
        was_solved = any(x.cache_is_correct for x in submissions)
        ctasks = check_single_chain(ctask.chain, team, preloaded_ctask=ctask)

        if ctask.t_is_locked and not data['is_admin']:
            raise Http404 # Bye

        if request.method == 'POST':
            if data['is_admin'] and 'delete-submission' in request.POST:
                submission_id = int(request.POST['delete-submission'])
                Submission.objects.filter(id=submission_id).delete()
                submissions = filter(lambda x: x.id != submission_id,
                        submissions) # Remove the deleted submission.

            if 'result' in request.POST:
                result = request.POST['result']
                if result and len(submissions) < ctask.max_submissions:
                    is_correct = ctask.check_result(result)
                    submission = Submission(ctask=ctask, team=team,
                            result=result, cache_is_correct=is_correct)
                    submission.save()
                    submissions.append(submission)

            is_solved = any(x.cache_is_correct for x in submissions)
            if was_solved != is_solved:
                delta = int(is_solved) - int(was_solved)
                team.cache_score += delta * ctask.score
                team.save()
        else:
            is_solved = was_solved

        data['submissions'] = submissions
        data['is_solved'] = is_solved
        data['submissions_left'] = ctask.max_submissions - len(submissions)

    data['ctask'] = ctask
    data['chain'] = ctask.chain
    return data


@competition_view(permission=EDIT)
@response('competition_chain_list.html')
def chain_list(request, competition, data):
    chains = Chain.objects.annotate(num_tasks=Count('competitiontask'))
    for chain in chains:
        chain.competition = competition
    data['chains'] = chains
    return data

def _create_or_update_task(instance, user, competition, chain, index, text):
    edit = bool(instance.task_id)
    if not edit:
        content = MathContent(text=text)
        content.save()
        task = Task(content=content, author=user, hidden=True)
    else:
        task = instance.task
        task.content.text = text
        task.content.save()

    task.name = u"{} - {} #{}".format(competition.name, chain.name, index + 1)
    task.source = competition.name
    task.save()

    if not edit:
        task_ct = ContentType.objects.get_for_model(Task)
        if competition.automatic_task_tags:
            add_task_tags(competition.automatic_task_tags, task, task_ct)
        if competition.admin_group:
            ObjectPermission.objects.create(content_object=task,
                    group=competition.admin_group, permission_type=VIEW)
            ObjectPermission.objects.create(content_object=task,
                    group=competition.admin_group, permission_type=EDIT)
        instance.task = task


@competition_view(permission=EDIT)
@response('competition_chain_new.html')
def chain_new(request, competition, data, chain_id=None):
    if chain_id:
        chain = get_object_or_404(Chain, id=chain_id)
        edit = True
    else:
        chain = None
        edit = False

    # CompetitionTaskFormSet = modelformset_factory(CompetitionTask,
    #         formset=BaseCompetitionTaskFormSet,
    #         fields=('correct_result', 'score'), extra=3)
    from competition.forms import CompetitionTaskForm
    CompetitionTaskFormSet = modelformset_factory(CompetitionTask,
            form=CompetitionTaskForm, formset=BaseCompetitionTaskFormSet,
            extra=5, can_order=True, can_delete=True)

    POST = request.POST if request.method == 'POST' else None
    chain_form = ChainForm(data=POST, instance=chain)
    queryset = CompetitionTask.objects.filter(chain_id=chain_id) \
            .select_related('task__content') \
            .order_by('chain_position')
    formset = CompetitionTaskFormSet(data=POST, queryset=queryset)

    if request.method == 'POST':
        if chain_form.is_valid() and formset.is_valid():
            chain = chain_form.save(commit=False)
            if not edit:
                chain.competition = competition
            chain.save()

            instances = formset.save(commit=False)
            for form in formset.ordered_forms:
                _index = form.cleaned_data['ORDER']
                if _index:
                    form.instance._index = _index
            for index, instance in enumerate(instances):
                instance.competition = competition
                instance.chain = chain
                instance.chain_position = getattr(instance, '_index', index)
                instance.max_submissions = competition.default_max_submissions

                _create_or_update_task(instance, request.user, competition,
                        chain, index, instance._text)

                instance.save()

            # Problems with existing formset... ahh, just refresh
            return (chain.get_absolute_url(), )

    data.update({
        'chain_form': chain_form,
        'formset': formset,
    })
    return data


def chain_edit(request, competition_id, chain_id):
    return chain_new(request, competition_id, chain_id=chain_id)


@competition_view()
@response('competition_notifications.html')
def notifications(request, competition, data):
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

    posts.sort(key=lambda post: post.date_created, reverse=True)

    data['posts'] = posts
    data['target_container'] = team
    data['team_member_ids'] = member_ids
    return data

@competition_view(permission=EDIT)
@response('competition_notifications_admin.html')
def notifications_admin(request, competition, data):
    team_ct = ContentType.objects.get_for_model(Team)

    posts = list(competition.posts.select_related('author', 'content'))
    team_posts = list(Post.objects.filter(content_type=team_ct) \
            .select_related('author', 'content'))
    user_id_to_team = \
            get_teams_for_user_ids([post.author_id for post in team_posts])
    for post in team_posts:
        post.t_team = user_id_to_team[post.author_id]

    posts += team_posts
    posts.sort(key=lambda post: post.date_created, reverse=True)

    data.update({
        'competition_ct': ContentType.objects.get_for_model(Competition),
        'post_form': PostsForm(placeholder="Poruka"),
        'posts': posts,
        'team_ct': team_ct,
        'teams': Team.objects.all(),
    })
    return data
