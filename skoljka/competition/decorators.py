from datetime import datetime
from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from skoljka.competition.models import Competition, Team, TeamMember
from skoljka.permissions.constants import EDIT, VIEW


def competition_view(permission=VIEW):
    """
    Decorator for competition views. Reads the Competition object and checks if
    the given user has the permission to view it.

    Expected function parameters:
        request, competition_id, (...)
    Decorated function parameters:
        request, competition, data, (...)

    TODO: arguments
    Decorator arguments:
        permission - permission to check

    TODO: data
    """

    def decorator(func):
        def inner(request, competition_id=None, *args, **kwargs):
            competition = get_object_or_404(Competition, id=competition_id)

            perm = competition.get_user_permissions(request.user)
            if permission not in perm:
                return HttpResponseForbidden(
                    "No permission to view this competition or do this action!"
                )

            is_admin = EDIT in perm
            current_time = datetime.now()
            has_started = competition.start_date < current_time
            has_finished = competition.end_date < current_time

            teams = []
            team_invitations = []
            team = None
            if request.user.is_authenticated():
                team_member_entries = list(
                    TeamMember.objects.select_related('team', 'team__author').filter(
                        team__competition_id=competition.id, member_id=request.user.id
                    )
                )

                for entry in team_member_entries:
                    status = entry.invitation_status
                    if status == TeamMember.INVITATION_ACCEPTED:
                        teams.append(entry.team)
                        if entry.is_selected:
                            team = entry.team
                    elif status == TeamMember.INVITATION_UNANSWERED:
                        team_invitations.append(entry.team)

            minutes_passed = (
                current_time - competition.start_date
            ).total_seconds() / 60
            nearly_finished = (
                not has_finished
                and (competition.end_date - current_time).total_seconds() < 1800
            )
            data = {
                'competition': competition,
                'team': team,
                'teams': teams,
                'team_invitations': team_invitations,
                'is_admin': is_admin,
                'has_private_team': any(
                    x for x in teams if x.team_type == Team.TYPE_ADMIN_PRIVATE
                ),
                'has_started': has_started,
                'has_finished': has_finished,
                'nearly_finished': nearly_finished,
                'current_time': current_time,
                'minutes_passed': minutes_passed,
                'is_scoreboard_frozen': current_time
                > competition.scoreboard_freeze_date,
            }
            return func(request, competition, data, *args, **kwargs)

        return wraps(func)(inner)

    return decorator
