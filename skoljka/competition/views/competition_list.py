from datetime import datetime

from skoljka.competition.models import Competition, TeamMember
from skoljka.permissions.constants import VIEW
from skoljka.utils.decorators import response

__all__ = ['competition_list', 'course_list']


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
