from django.http import Http404
from django.shortcuts import get_object_or_404

from skoljka.activity import action as _action
from skoljka.competition.decorators import competition_view
from skoljka.competition.models import Submission
from skoljka.competition.templatetags.competition_tags import get_submission_actions
from skoljka.competition.utils import refresh_teams_cache_score
from skoljka.permissions.constants import EDIT
from skoljka.utils.decorators import response

__all__ = ['submission_detail']


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
