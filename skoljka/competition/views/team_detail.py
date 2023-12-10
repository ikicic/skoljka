from django.shortcuts import get_object_or_404

from skoljka.competition.decorators import competition_view
from skoljka.competition.models import Submission, Team, TeamMember
from skoljka.utils.decorators import response

__all__ = ['team_detail']


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
