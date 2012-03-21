from django.db import models
from django.contrib.auth.models import User

from mathcontent.models import MathContent
from post.generic import PostGenericRelation
from rating.fields import RatingField
from rating.constants import *
from task.models import Task

SOLUTION_RATING_ATTRS = {
    'range': 5,
    'titles': [u'Netočno', u'Točno uz manje nedostatke.', u'Točno.', u'Točno i domišljato.', u'Genijalno! Neviđeno!'],
}

# TODO: nekako drugacije ovo nazvati
SOLUTION_CORRECT_SCORE = 2

# solution.status
STATUS = {'blank': 0, 'as_solved': 1, 'todo': 2, 'submitted': 3}

HTML_INFO = {
    'blank': {'label_class': '', 'label_text': '', 'tr_class': ''},
    'as_solved': {'label_class': 'label-success', 'label_text': u'Riješeno', 'tr_class': 'task_as_solved'},
    'solved': {'label_class': 'label-success', 'label_text': u'Točno', 'tr_class': 'task_solved'},
    'wrong': {'label_class': 'label-important', 'label_text': u'Netočno', 'tr_class': 'task_wrong'},
    'todo': {'label_class': 'label-warning', 'label_text': u'To Do', 'tr_class': 'task_todo'},
    'submitted_not_rated': {'label_class': 'label-info', 'label_text': u'Poslano', 'tr_class': 'task_submitted_not_rated'},
}

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
