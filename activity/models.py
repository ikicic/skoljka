from django.db import models
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from activity.constants import *

# ... jako nedovrseno ...

class Action(models.Model):
    actor = models.ForeignKey(User, db_index=True)
    type = models.IntegerField(db_index=True)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    
    target_id = models.IntegerField(blank=True, db_index=True)
    action_object_id = models.IntegerField(blank=True, db_index=True)
    
    text = models.TextField(blank=True)

    def A(self, model, text):
        return u'<a href="%s/%d/">%s</a>' % (model, self.action_object_id, text)
        
    def T(self, model, text):
        return u'<a href="%s/%d/">%s</a>' % (model, self.target_id, text)
        
    def U(self):
        return u'<a href="userprofile/%d/">%s</a>' % (self.actor_id, self.actor.get_full_name())
    
    def get_message(self):
        S = ''
        if self.type == SOLUTION_SUBMIT:
            S = u'je poslao %s za zadatak' % self.A('solution', u'rješenje')
        elif self.type == SOLUTION_AS_SOLVED:
            S = u'je označio kao riješen zadatak'
        elif self.type == SOLUTION_TODO:
            S = u'je označio s ToDo zadatak'
        return mark_safe(S)
        
    def get_content(self):
        S = ''
        if self.type in [SOLUTION_SUBMIT, SOLUTION_AS_SOLVED, SOLUTION_TODO, SOLUTION_AS_OFFICIAL]:
            from task.models import Task
            S = u'<a href="task/%d/">%s</a>' % (self.target_id, Task.objects.get(id=self.target_id).name)
        return mark_safe(S)