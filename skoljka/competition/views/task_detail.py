from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404

from skoljka.competition.decorators import competition_view
from skoljka.competition.evaluator import (
    get_evaluator,
    get_sample_solution,
    get_solution_help_text,
    safe_parse_descriptor,
)
from skoljka.competition.forms import CompetitionSolutionForm
from skoljka.competition.models import CompetitionTask, Submission
from skoljka.competition.templatetags.competition_tags import get_submission_actions
from skoljka.competition.utils import (
    load_and_preprocess_chain,
    update_ctask_cache_admin_solved_count,
    update_score_on_ctask_action,
)
from skoljka.mathcontent.forms import MathContentForm
from skoljka.utils.decorators import response

__all__ = ['task_detail']


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
