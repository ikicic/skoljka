from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.forms.models import modelformset_factory
from django.shortcuts import get_object_or_404

from mathcontent.models import MathContent
from permissions.constants import VIEW, EDIT
from permissions.models import ObjectPermission
from skoljka.libs.decorators import response
from tags.utils import add_task_tags
from task.models import Task

from competition.decorators import competition_view
from competition.forms import ChainForm, CompetitionTask, \
        BaseCompetitionTaskFormSet, TeamForm
from competition.models import Chain, Competition, CompetitionTask, Team, \
        TeamMember

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

@competition_view()
@response('competition_registration.html')
def registration(request, competition, data):
    if not data['is_admin'] \
            and datetime.now() < competition.registration_open_date:
        return HttpResponseRedirect(competition.get_absolute_url())

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
    all_ctasks = CompetitionTask.objects.filter(competition=competition) \
            .select_related('task__content')
    # TODO: time!
    _all_chains = Chain.objects.filter(competition=competition)
    all_chains_dict = {chain.id: chain for chain in _all_chains}

    class Category(object):
        def __init__(self, name):
            self.name = name
            self.chains = []

    categories = {}

    # Use preloaded data
    for ctask in all_ctasks:
        chain = all_chains_dict[ctask.chain_id]
        ctask.competition = competition
        ctask.chain = chain

        if not hasattr(chain, 'ctasks'):
            chain.ctasks = []
        chain.ctasks.append(ctask)

    for chain_id, chain in all_chains_dict.iteritems():
        chain.competition = competition

        if chain.category not in categories:
            categories[chain.category] = Category(chain.category)
        categories[chain.category].chains.append(chain)

    data.update({
        'categories': categories
    })
    return data


@competition_view(registered=True)
@response('competition_task_detail.html')
def task_detail(request, competition, data, ctask_id):
    ctask = get_object_or_404(
            CompetitionTask.objects.select_related('task', 'task__content'),
            competition=competition, id=ctask_id)

    data.update({
        'ctask': ctask,
        'task': ctask.task
    })
    return data


@competition_view(permission=EDIT)
@response('competition_chain_list.html')
def chain_list(request, competition, data):
    data['chains'] = Chain.objects.annotate(num_tasks=Count('competitiontask'))
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

    task.name = "{} - {} #{}".format(competition.name, chain.name, index + 1)
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
            extra=3, can_order=True, can_delete=True)

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
            return (request.get_full_path(), )



    data.update({
        'chain_form': chain_form,
        'formset': formset,
    })
    return data


def chain_edit(request, competition_id, chain_id):
    return chain_new(request, competition_id, chain_id=chain_id)
