from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils.html import mark_safe

from mathcontent.models import MathContent
from permissions.constants import VIEW, VIEW_SOLUTIONS
from post.generic import PostGenericRelation
from rating.fields import RatingField
from task.models import Task
from skoljka.utils.decorators import autoconnect
from skoljka.utils.models import ModelEx


# TODO: nekako drugacije ovo nazvati
SOLUTION_CORRECT_SCORE = 2.6

# solution.status
STATUS = {'blank': 0, 'as_solved': 1, 'todo': 2, 'submitted': 3}

# Key names of detailed states.
# For more info, look at Solution._calc_detailed_status()
# If you need to change the order, don't forget to update _calc_detailed_status()
DETAILED_STATUS_NAME = ['blank', 'as_solved', 'todo', 'submitted_not_rated',
    'wrong', 'correct']
DETAILED_STATUS = {name: i for i, name in enumerate(DETAILED_STATUS_NAME)}

# Each element of HTML_INFO is dict with keys from _HTML_INFO_KEYS and values
# from _HTML_INFO
#                                               task label, solution tr
_HTML_INFO_KEYS = ('label_class', 'label_text', 'tr_class', 'sol_rgb')
_HTML_INFO = {
    'blank': ('', '', '', None),
    'as_solved': ('label-success', u'Riješeno', 'task-as-solved', (170, 255, 170)),
    'todo': ('label-warning', u'To Do', 'task-todo', None),
    'submitted_not_rated': ('label-info', u'Poslano', 'task-submitted-not-rated', (255, 219, 76)),
    'wrong': ('label-important', u'Netočno', 'task-wrong', (255, 150, 150)),
    'correct': ('label-success', u'Točno', 'task-correct', (112, 255, 112)),
}

# status number -> dict(info_key -> value)
HTML_INFO = {DETAILED_STATUS[key]: dict(zip(_HTML_INFO_KEYS, value))
    for key, value in _HTML_INFO.iteritems()}


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
        in case solution correctness is changed.
    """
    if solution.status != STATUS['submitted']:
        return # not interesting

    old = old_value >= SOLUTION_CORRECT_SCORE
    new = new_value >= SOLUTION_CORRECT_SCORE

    if old != new:
        _update_solved_count(new - old, solution.task,
            solution.author.get_profile())


SOLUTION_RATING_ATTRS = {
    'range': 6,
    'titles': [u'Neocijenjeno', u'Netočno', u'Točno uz manje nedostatke.',
        u'Točno.', u'Točno i domišljato.', u'Genijalno! Neviđeno!'],
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
                Q(task__permissions__group_id__in=user_group_ids,
                    task__permissions__permission_type=VIEW)    \
                | Q(task__author_id=user.id)    \
                | Q(task__hidden=False)).distinct()
        elif permission_type == VIEW:
            return self.filter(hidden=False)
        else:
            return self.none()

@autoconnect
class Solution(ModelEx):
    task = models.ForeignKey(Task)
    author = models.ForeignKey(User)
    content = models.ForeignKey(MathContent, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_edit_time = models.DateTimeField(auto_now=True)  # only for submitted
    posts = PostGenericRelation()

    status = models.IntegerField(default=STATUS['blank']) # view STATUS for more info

    # More like a cached value. Note that this value is automatically refreshed
    # in pre_save, not before that.
    detailed_status = models.IntegerField(default=DETAILED_STATUS['blank'],
        db_index=True)

    is_official = models.BooleanField()
    correctness = RatingField(**SOLUTION_RATING_ATTRS)

    # Custom manager
    objects = SolutionManager()

    class Meta:
        unique_together=(('task', 'author'),)
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
            Detailed status, unlike normal .status, describes also the
            correctness of the solution.
        """

        # The only special case actually...
        if self.status == STATUS['submitted']:
            if self.correctness_avg < 1e-6:
                return DETAILED_STATUS['submitted_not_rated']
            elif self.correctness_avg < SOLUTION_CORRECT_SCORE:
                return DETAILED_STATUS['wrong']
            else:
                return DETAILED_STATUS['correct']

        # Otherwise, the order is the same...
        return self.status

    def pre_save(self):
        self.detailed_status = self._calc_detailed_status()

    def is_solved(self):
        return self.is_as_solved() or self.is_correct()

    def is_correct(self):
        # return self.is_submitted() and self.correctness_avg >= SOLUTION_CORRECT_SCORE
        return self.detailed_status == DETAILED_STATUS['correct']

    def is_submitted(self):
        return self.status == STATUS['submitted']

    def is_as_solved(self):
        return self.status == STATUS['as_solved']

    def is_todo(self):
        return self.status == STATUS['todo']

    def is_blank(self):
        return self.status == STATUS['blank']   # exists, but it's blank

    def _get_user_solution(self, user, users_solution):
        # if user's solution not given, search for it
        if users_solution is 0:
            try:
                users_solution = Solution.objects.get(author=user,
                    task_id=self.task_id)
            except Solution.DoesNotExist:
                return None
        return users_solution

    def check_accessibility(self, user, users_solution=0):
        """
            Checks if the user can view the solution, and if it should be
            obfuscated.
            Returns pair of booleans:
                can_view, should_obfuscate

            The result depends on:
                Task solution settings  (can_view)
                Explicit permission     (can_view)
                Did user solve the task (can_view, should_obfuscate)
                Profile preferences     (should_obfuscate)

            If users_solution is not given, it will be manually retrieved.
            As this method checks task.solution_settings, it is preferable that
            task is already loaded.
        """
        # The implentation is quite complex, because there are millions of
        # different cases. When updating, please make sure everything is
        # correct.
        task_settings = self.task.solution_settings

        if not user.is_authenticated():
            # obfuscate by default
            return task_settings == Task.SOLUTIONS_VISIBLE, True

        if self.author_id == user.id:
            return True, False # always show my own solutions

        if task_settings != Task.SOLUTIONS_VISIBLE:
            # Currently, the task's author can't make solutions unavailable
            # to himself/herself.
            can_view = getattr(self.task, '_cache_can_view_solutions', False)  \
                or self.task.user_has_perm(user, VIEW_SOLUTIONS)

            # Also, solution check may be done before the explicit permission
            # check. Not a big performance difference, both are assumed to be
            # preloaded anyway.
            if not can_view:
                if task_settings == Task.SOLUTIONS_NOT_VISIBLE:
                    return False, True      # bye
                elif task_settings == Task.SOLUTIONS_VISIBLE_IF_ACCEPTED:
                    users_solution = self._get_user_solution(user, users_solution)
                    if not users_solution or not users_solution.is_correct():
                        return False, True     # can't view solution, bye

        # Ok, now the user definitely has the right to view the solution.
        # Now we have to check if he/she wants to view it.

        # check user settings
        profile = user.get_profile()
        if profile.show_unsolved_task_solutions     \
                or self.task.difficulty_rating_avg < profile.hide_solution_min_diff:
            # Show always, or because it's too easy. Note that if the min_diff
            # option is not set, the comparison will always be False!
            return True, False

        # Load, if not loaded yet.
        users_solution = self._get_user_solution(user, users_solution)

        # if there is no solution -> obfuscate
        # if there is, check if it is solved
        return True, not users_solution or not users_solution.is_solved()


# nuzno(?) da bi queryji koristili JOIN, a ne subqueryje
# TODO: neki prikladniji naziv za related_name
User.add_to_class('solutions', models.ManyToManyField(Task, through=Solution, related_name='solutions_by'))
