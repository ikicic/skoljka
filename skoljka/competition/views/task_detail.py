import datetime

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
from skoljka.competition.forms import SubmissionForm
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
    view = _TaskDetailView(request, competition, data, ctask_id)

    if not view.has_access_to_chain():
        raise Http404

    evaluator, variables = view.parse_descriptor()

    response = view.handle_admin_post()
    if response:
        return response

    chain_ctasks, chain_submissions, submissions = view.load_chain_and_submissions(
        team=view.team
    )
    if not view.has_access_to_ctask():
        raise Http404

    data['submissions_closed'] = view.are_submissions_closed()
    if view.can_submit_solutions():
        response = view.handle_form(
            evaluator, chain_ctasks, chain_submissions, submissions
        )
        if response:
            return response
        if view.chain.close_minutes:
            data['chain_open_until'] = competition.start_date + datetime.timedelta(
                minutes=view.chain.close_minutes
            )

    if view.ctask.is_manually_graded():
        view.handle_manual_grading_submission(submissions, data)

    if view.is_admin:
        data['all_ctask_submissions'] = view.get_all_ctask_submissions()

    data['help_text'] = get_solution_help_text(variables)
    data['chain'] = view.ctask.chain
    data['ctask'] = view.ctask
    data['is_solved'] = any(x.score for x in submissions)
    data['submissions'] = submissions
    data['submissions_left'] = view.ctask.max_submissions - len(submissions)

    if (
        competition.show_solutions
        and data['has_finished']
        and not data.get('is_solved', False)
    ):
        data['sample_solution'] = get_sample_solution(variables)

    return data


class _TaskDetailView(object):
    def __init__(self, request, competition, data, ctask_id):
        self.request = request
        self.competition = competition
        self.data = data
        self.is_admin = data['is_admin']
        self.team = data['team']

        extra = ['task__author'] if self.is_admin else []
        self.ctask = get_object_or_404(
            CompetitionTask.objects.select_related(
                'chain', 'task', 'task__content', *extra
            ),
            competition=competition,
            id=ctask_id,
        )
        self.ctask.competition = competition
        self.chain = self.ctask.chain
        if self.chain:
            self.chain.competition = competition

    def has_access_to_chain(self):
        """Returns whether the user has the access to see the current chain."""
        if self.is_admin:
            return True
        data = self.data
        ctask = self.ctask
        return (
            (self.team or data['has_finished'])
            and data['has_started']
            and ctask.chain
            and ctask.chain.unlock_minutes <= data['minutes_passed']
            and ctask.chain.team_has_access(self.team)
        )

    def parse_descriptor(self):
        evaluator = get_evaluator(self.competition.evaluator_version)
        variables = safe_parse_descriptor(evaluator, self.ctask.descriptor)
        return evaluator, variables

    def handle_admin_post(self):
        request = self.request
        if (
            self.is_admin
            and request.method == 'POST'
            and 'delete-submission' in request.POST
        ):
            try:
                submission = Submission.objects.select_related('team').get(
                    id=request.POST['delete-submission'],
                    ctask=self.ctask,
                )
            except Submission.DoesNotExist:
                return None  # Silently ignore.

            submission_team = submission.team
            chain_ctasks, old_submissions, _ = self.load_chain_and_submissions(
                team=submission_team
            )
            new_submissions = [s for s in old_submissions if s != submission]
            submission.delete()

            self._update_submission_caches(
                chain_ctasks, submission_team, old_submissions, new_submissions
            )

            # Prevent form resubmission.
            return (self.ctask.get_absolute_url(),)

        return None

    def load_chain_and_submissions(self, team=None):
        """Load all ctasks of the chain and given team's submissions to these
        ctasks, and compute which ctasks are locked, which not.

        Note: self.ctask is updated as well.

        Returns:
            (chain ctasks, chain submissions, this ctask's submissions)
        """
        chain_ctasks, chain_submissions = load_and_preprocess_chain(
            self.competition, self.ctask.chain, team=team, preloaded_ctask=self.ctask
        )
        submissions = [s for s in chain_submissions if s.ctask_id == self.ctask.id]
        submissions.sort(key=lambda x: x.date)
        return chain_ctasks, chain_submissions, submissions

    def _update_submission_caches(
        self, chain_ctasks, team, old_chain_submissions, new_chain_submissions
    ):
        """Update the team-related cache. Note that the team may be different
        from self.team, e.g. when deleting submissions."""
        ctask = self.ctask
        if team.is_admin_private():
            update_ctask_cache_admin_solved_count(self.competition, ctask, ctask.chain)
        if ctask.chain:
            update_score_on_ctask_action(
                self.competition,
                team,
                ctask.chain,
                chain_ctasks=chain_ctasks,
                old_chain_submissions=old_chain_submissions,
                new_chain_submissions=new_chain_submissions,
            )

    def are_submissions_closed(self):
        """Return if the chain is closed according to chain.close_minutes."""
        chain = self.chain
        return chain and chain.is_closed(minutes_passed=self.data['minutes_passed'])

    def can_submit_solutions(self):
        """Return whether the active team has a permission to submit solutions
        at the current moment. It is assumed that the team has the view access.
        The function does not check the number of existing submission or whether
        the team already solved the task. This is handled in `handle_form`."""
        if not self.team:
            return False
        if self.is_admin:
            return True
        if self.data['has_finished']:
            return False
        return not self.are_submissions_closed()

    def has_access_to_ctask(self):
        """Return whether the user has access to the ctask, assuming they have
        an access to the chain. `load_chain_and_submissions` must be called
        before this function."""
        return self.is_admin or not self.ctask.t_is_locked

    def handle_form(self, evaluator, chain_ctasks, chain_submissions, submissions):
        if self.ctask.is_automatically_graded():
            return self._handle_automatic_grading_form(
                evaluator, chain_ctasks, chain_submissions, submissions
            )
        else:
            assert self.ctask.is_manually_graded(), self.ctask
            return self._handle_manual_grading_form(submissions)

    def _handle_automatic_grading_form(
        self, evaluator, chain_ctasks, chain_submissions, submissions
    ):
        assert self.can_submit_solutions()

        ctask = self.ctask
        if (
            self.request.method == 'POST'
            and len(submissions) < ctask.max_submissions
            and not ctask.t_is_solved
        ):
            solution_form = SubmissionForm(
                self.request.POST, descriptor=ctask.descriptor, evaluator=evaluator
            )
            if solution_form.is_valid():
                result = solution_form.cleaned_data['result']
                is_correct = evaluator.check_result(ctask.descriptor, result)
                submission = Submission(
                    ctask=ctask,
                    team=self.team,
                    result=result,
                    score=is_correct * ctask.max_score,
                )
                submission.save()
                new_chain_submissions = chain_submissions + [submission]
                self._update_submission_caches(
                    chain_ctasks, self.team, chain_submissions, new_chain_submissions
                )

                # Prevent form resubmission.
                return (ctask.get_absolute_url(),)
        else:
            solution_form = SubmissionForm(
                descriptor=ctask.descriptor, evaluator=evaluator
            )

        self.data['solution_form'] = solution_form

    def _handle_manual_grading_form(self, submissions):
        assert self.can_submit_solutions()

        data = self.data
        if submissions:
            # If it somehow happens that there is more than one submission,
            # consider only the first one.
            submission = submissions[0]
            content = submission.content
        else:
            submission = content = None

        content_form = MathContentForm(self.request.POST or None, instance=content)
        if self.request.method == 'POST' and content_form.is_valid():
            content_form = MathContentForm(self.request.POST, instance=content)
            content = content_form.save()
            if not submission:
                submission = Submission(
                    ctask=self.ctask,
                    team=self.team,
                    content=content,
                    result=settings.COMPETITION_MANUAL_GRADING_TAG,
                )
            submission.mark_unseen_team_activity()
            submission.save()

            # There is no score update update, because grading is done
            # separately by moderators. Redirect to prevent form resubmission.
            return (self.ctask.get_absolute_url(),)

        data['content_form'] = content_form

    def handle_manual_grading_submission(self, submissions, data):
        if not submissions:
            return

        # If it somehow happens that there is more than one submission,
        # consider only the first one.
        submission = submissions[0]
        data['submission'] = submission
        data['submission_actions'], data['not_graded'] = get_submission_actions(
            submission
        )
        if (
            submission.oldest_unseen_admin_activity
            != Submission.NO_UNSEEN_ACTIVITIES_DATETIME
        ):
            data['unread_newer_than'] = submission.oldest_unseen_admin_activity
            submission.oldest_unseen_admin_activity = (
                Submission.NO_UNSEEN_ACTIVITIES_DATETIME
            )
            submission.save()

    def get_all_ctask_submissions(self):
        ctask = self.ctask
        all_ctask_submissions = list(
            Submission.objects.filter(ctask_id=ctask.id)
            .select_related('team')
            .order_by('id')
        )
        for submission in all_ctask_submissions:
            submission.team.competition = self.competition
            submission.ctask = ctask
        return all_ctask_submissions
