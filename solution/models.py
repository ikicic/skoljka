from django.db import models
from django.contrib.auth.models import User

from mathcontent.models import MathContent
from post.generic import PostGenericRelation
from rating.fields import RatingField
from task.models import Task


# TODO: nekako drugacije ovo nazvati
SOLUTION_CORRECT_SCORE = 2.6

# solution.status
STATUS = {'blank': 0, 'as_solved': 1, 'todo': 2, 'submitted': 3}

# Each element of HTML_INFO is dict with keys from _HTML_INFO_KEYS and values
# from _HTML_INFO
_HTML_INFO_KEYS = ('label_class', 'label_text', 'tr_class')
_HTML_INFO = {
    'blank': ('', '', ''),
    'as_solved': ('label-success', u'Riješeno', 'task_as_solved'),
    'solved': ('label-success', u'Točno', 'task_solved'),
    'wrong': ('label-important', u'Netočno', 'task_wrong'),
    'todo': ('label-warning', u'To Do', 'task_todo'),
    'submitted_not_rated': ('label-info', u'Poslano', 'task_submitted_not_rated'),
}

HTML_INFO = {key: dict(zip(_HTML_INFO_KEYS, value)) for key, value in _HTML_INFO.iteritems()}


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

class Solution(models.Model):
    task = models.ForeignKey(Task)
    author = models.ForeignKey(User)
    content = models.ForeignKey(MathContent, blank=True, null=True) # a ipak sam stavio null...
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_edit_time = models.DateTimeField(auto_now=True)  # only for submitted
    posts = PostGenericRelation()

    status = models.IntegerField(default=STATUS['blank']) # view STATUS for more info
    is_official = models.BooleanField()
    correctness = RatingField(**SOLUTION_RATING_ATTRS)

    class Meta:
        unique_together=(('task', 'author'),)

    def get_absolute_url(self):
        return '/solution/%d/' % self.id

    # template helpers
    def get_html_info(self):
        if self.status == STATUS['as_solved']:
            return HTML_INFO['as_solved']
        if self.status == STATUS['submitted']:
            if self.correctness_avg == 0.0:
                return HTML_INFO['submitted_not_rated']
            return HTML_INFO['solved' if self.is_correct() else 'wrong']
        if self.status == STATUS['todo']:
            return HTML_INFO['todo']
        return HTML_INFO['blank']

    def is_solved(self):
        return self.is_as_solved() or self.is_correct()

    def is_correct(self):
        return self.is_submitted() and self.correctness_avg >= SOLUTION_CORRECT_SCORE

    def is_submitted(self):
        return self.status == STATUS['submitted']

    def is_as_solved(self):
        return self.status == STATUS['as_solved']

    def is_todo(self):
        return self.status == STATUS['todo']

    def is_blank(self):
        return self.status == STATUS['blank']   # postoji, ali blank

    def should_obfuscate(self, user, users_solution=0):
        """
            Check if the user should see the content of this solution.
            If users_solution is not given, it will be manually retrieved.
        """
        if not user.is_authenticated():
            return True # default options is to hide solutions

        if self.author == user:
            return False # always show my own solutions

        # check user settings
        profile = user.get_profile()
        if profile.show_unsolved_task_solutions     \
                or self.task.difficulty_rating_avg < profile.hide_solution_min_diff:
            # Show always, or because it's too easy. Note that if the min_diff
            # option is not set, the comparison will always be False!
            return False

        # if user's solution not given, search for it
        if users_solution is 0:
            try:
                users_solution = Solution.objects.get(author=user,
                    task_id=self.task_id)
            except Solution.DoesNotExist:
                return True

        # if there is no solution -> obfuscate
        # if there is, check if it is solved
        return not users_solution or not users_solution.is_solved()


# nuzno(?) da bi queryji koristili JOIN, a ne subqueryje
# TODO: neki prikladniji naziv za related_name
User.add_to_class('solutions', models.ManyToManyField(Task, through=Solution, related_name='solutions_by'))
