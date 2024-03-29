﻿from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q

from skoljka.activity.constants import SOLUTION_RATE
from skoljka.mathcontent.models import MathContent
from skoljka.permissions.constants import VIEW
from skoljka.post.generic import PostGenericRelation
from skoljka.rating.fields import RatingField
from skoljka.task.models import Task
from skoljka.utils.decorators import autoconnect
from skoljka.utils.models import ModelEx

# TODO: nekako drugacije ovo nazvati
# 0 = unrated, 1 = incorrect, 2 = correct... tehnical details...
SOLUTION_CORRECT_SCORE = 1.6  # 'incorrect' has preference over 'correct'


class SolutionStatus:
    BLANK = 0
    AS_SOLVED = 1
    TODO = 2
    SUBMITTED = 3


SOLUTION_STATUS_BY_NAME = {
    'blank': SolutionStatus.BLANK,
    'as_solved': SolutionStatus.AS_SOLVED,
    'todo': SolutionStatus.TODO,
    'submitted': SolutionStatus.SUBMITTED,
}

_USERS_SOLUTION_NOT_PROVIDED = object()

# Key names of detailed states.
# For more info, look at Solution._calc_detailed_status()
# If you need to change the order, don't forget to update _calc_detailed_status()
class SolutionDetailedStatus:
    BLANK = 0
    AS_SOLVED = 1
    TODO = 2
    SUBMITTED_NOT_RATED = 3
    SUBMITTED_INCORRECT = 4
    SUBMITTED_CORRECT = 5


SOLUTION_DETAILED_STATUS_MAX = 5  # Max value

# Each element of HTML_INFO is dict with keys from _HTML_INFO_KEYS and values
# from _HTML_INFO
#                                               task label, solution tr
_HTML_INFO_KEYS = ('label_class', 'label_text', 'tr_class', 'sol_rgb')
_HTML_INFO = {
    SolutionDetailedStatus.BLANK: ('', '', '', None),
    SolutionDetailedStatus.AS_SOLVED: (
        'label-success',
        u"Riješeno",
        'task-as-solved',
        (170, 255, 170),
    ),
    SolutionDetailedStatus.TODO: ('label-warning', u'To Do', 'task-todo', None),
    SolutionDetailedStatus.SUBMITTED_NOT_RATED: (
        'label-info',
        u"Poslano",
        'task-submitted-not-rated',
        (255, 219, 76),
    ),
    SolutionDetailedStatus.SUBMITTED_INCORRECT: (
        'label-important',
        u"Netočno",
        'task-wrong',
        (255, 150, 150),
    ),
    SolutionDetailedStatus.SUBMITTED_CORRECT: (
        'label-success',
        u"Točno",
        'task-correct',
        (112, 255, 112),
    ),
}

# status number -> dict(info_key -> value)
HTML_INFO = {
    key: dict(zip(_HTML_INFO_KEYS, value)) for key, value in _HTML_INFO.iteritems()
}


def _update_solved_count(delta, task, profile, save_task=True, save_profile=True):
    """
    Update solution counter for given Task and UserProfile.

    To disable automatic saving, set save_task and/or save_profile to False.
    """
    if delta == 0:
        return

    task.solved_count += delta
    if save_task:
        task.save()

    profile.solved_count += delta
    profile.update_diff_distribution(task, delta)
    if save_profile:
        profile.save()


def _solution_on_update(solution, field_name, old_value, new_value):
    """
    Updates statistics (number of correct solution for Task and UserProfile)
    in the case solution correctness is changed.
    """
    if solution.status != SolutionStatus.SUBMITTED:
        return  # not interesting

    old = old_value >= SOLUTION_CORRECT_SCORE
    new = new_value >= SOLUTION_CORRECT_SCORE

    if old != new:
        _update_solved_count(new - old, solution.task, solution.author.get_profile())


SOLUTION_RATING_ATTRS = {
    'range': 3,
    'titles': [u"Neocijenjeno", u"Netočno", u"Točno"],
    'action_type': SOLUTION_RATE,
    'on_update': _solution_on_update,
}


class SolutionManager(models.Manager):
    def filter_visible_tasks_for_user(self, user):
        """
        Filter tasks visible to the given user.
        Does not check anything related to solution itself.
        """
        if user is not None and user.is_authenticated():
            user_group_ids = user.get_profile().get_group_ids()
            return self.filter(
                Q(
                    task__objpermissions__group_id__in=user_group_ids,
                    task__objpermissions__permission_type=VIEW,
                )
                | Q(task__author_id=user.id)
                | Q(task__hidden=False)
            ).distinct()
        else:
            return self.filter(task__hidden=False)


@autoconnect
class Solution(ModelEx):
    task = models.ForeignKey(Task)
    author = models.ForeignKey(User)
    content = models.ForeignKey(MathContent, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_edit_time = models.DateTimeField(auto_now=True)  # only for submitted
    posts = PostGenericRelation(placeholder="Komentar")

    status = models.IntegerField(default=SolutionStatus.BLANK)

    # More like a cached value. Note that this value is automatically refreshed
    # in pre_save, not before that.
    detailed_status = models.IntegerField(
        default=SolutionDetailedStatus.BLANK, db_index=True
    )

    is_official = models.BooleanField()
    correctness = RatingField(**SOLUTION_RATING_ATTRS)

    # Custom manager
    objects = SolutionManager()

    class Meta:
        unique_together = (('task', 'author'),)
        # TODO: Django 1.5. In the meantime list here all multi-indices.
        # index_together = (('detailed_status', 'date_created'), )

    def remember_original(self):
        # ModelEx stuff
        self._original_detailed_status = self.detailed_status

    def get_absolute_url(self):
        return '/solution/%d/' % self.id

    # template helpers
    def get_html_info(self):
        return HTML_INFO[self.detailed_status]

    def _calc_detailed_status(self):
        """
        Detailed status, unlike normal .status, describes also the correctness
        of the solution.
        """

        # The only special case actually...
        if self.status == SolutionStatus.SUBMITTED:
            if self.correctness_avg < 1e-6:
                return SolutionDetailedStatus.SUBMITTED_NOT_RATED
            elif self.correctness_avg < SOLUTION_CORRECT_SCORE:
                return SolutionDetailedStatus.SUBMITTED_INCORRECT
            else:
                return SolutionDetailedStatus.SUBMITTED_CORRECT

        # Otherwise, the order is the same...
        return self.status

    def pre_save(self):
        self.detailed_status = self._calc_detailed_status()

    def is_solved(self):
        return self.is_as_solved() or self.is_correct()

    def is_correct(self):
        # return self.is_submitted() and self.correctness_avg >= SOLUTION_CORRECT_SCORE
        return self.detailed_status == SolutionDetailedStatus.SUBMITTED_CORRECT

    def is_submitted(self):
        return self.status == SolutionStatus.SUBMITTED

    def is_as_solved(self):
        return self.status == SolutionStatus.AS_SOLVED

    def is_todo(self):
        return self.status == SolutionStatus.TODO

    def is_blank(self):
        return self.status == SolutionStatus.BLANK

    def _get_user_solution(self, user, users_solution):
        # if user's solution not given, search for it
        if users_solution is _USERS_SOLUTION_NOT_PROVIDED:
            try:
                users_solution = Solution.objects.get(author=user, task_id=self.task_id)
            except Solution.DoesNotExist:
                return None
        return users_solution

    def can_edit(self, user):
        """
        Determine if given user is allowed to edit the existing solution.

        Currently, only authors themselves and staff can edit the solution.
        Note that staff won't be able to edit solutions of inaccessible tasks.
        """
        return self.author_id == user.id or user.is_staff

    def should_obfuscate(self, user, users_solution=_USERS_SOLUTION_NOT_PROVIDED):
        """
        Checks if the solution should be obfuscated prior showing it to the user.

        It is assumed that the user has acesss to the task.

        The result depends on:
            Did user solve the task
            Profile preferences

        If users_solution is not given, it will be manually retrieved.
        """
        if not user.is_authenticated():
            return True  # Obfuscate by default.

        if self.author_id == user.id:
            return False  # Always show my own solutions.

        # Check if the user wants to see the solution immediately.
        profile = user.get_profile()
        if not profile.check_solution_obfuscation_preference(
            self.task.difficulty_rating_avg
        ):
            return False  # User is fine with seeing the solution.

        # Load, if not loaded yet.
        users_solution = self._get_user_solution(user, users_solution)

        # if there is no solution -> obfuscate
        # if there is, check if it is solved
        return not users_solution or not users_solution.is_solved()


# nuzno(?) da bi queryji koristili JOIN, a ne subqueryje
# TODO: neki prikladniji naziv za related_name
User.add_to_class(
    'solutions',
    models.ManyToManyField(Task, through=Solution, related_name='solutions_by'),
)
