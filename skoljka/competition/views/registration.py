from django.shortcuts import get_object_or_404

from skoljka.competition.decorators import competition_view
from skoljka.competition.forms import TeamForm
from skoljka.competition.models import Team, TeamMember
from skoljka.userprofile.forms import AuthenticationFormEx
from skoljka.utils.decorators import response

__all__ = ['registration']


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
