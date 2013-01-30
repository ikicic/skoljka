from django.db import models
from django.contrib.auth.models import User

from mathcontent.models import MathContent
from post.generic import PostGenericRelation
from rating.fields import RatingField
from rating.constants import *
from task.models import Task

SOLUTION_RATING_ATTRS = {
    'range': 5,
    'titles': [u'Netočno', u'Točno uz manje nedostatke.', u'Točno.',
        u'Točno i domišljato.', u'Genijalno! Neviđeno!'],
}

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


class Solution(models.Model):
    task = models.ForeignKey(Task)
    author = models.ForeignKey(User)
    content = models.ForeignKey(MathContent, blank=True, null=True)     # a ipak sam stavio null...
    date_created = models.DateTimeField(auto_now_add=True)
    last_edit_time = models.DateTimeField(auto_now=True)
    posts = PostGenericRelation()
    
    status = models.IntegerField()
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
        
# nuzno(?) da bi queryji koristili JOIN, a ne subqueryje
# TODO: neki prikladniji naziv za related_name
User.add_to_class('solutions', models.ManyToManyField(Task, through=Solution, related_name='solutions_by'))
