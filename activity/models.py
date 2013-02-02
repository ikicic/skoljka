from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from activity.constants import *
from userprofile.templatetags.userprofile_tags import userlink

# TODO: napraviti neki shortcut za ttype = (A.type, A.subtype)

# 3. 4. 2012. (ikicic) Znam da ovo nije najpametnije izvedeno, pa evo neki prijedlozi:
# 1) da Action pamti reply_to ForeignKey na Post, tj. ID poruke na koju je self odgovor
# 2) da Action sam moze konstruirati link u kojem se nalazi
#    (npr. da sam zna /task/%d/#post%d, /solution/%d/#post%d itd.)

# na temelju https://github.com/justquick/django-activity-stream/
# odnosno https://github.com/justquick/django-activity-stream/blob/master/actstream/models.py
class Action(models.Model):
    actor = models.ForeignKey(User, db_index=True)
    type = models.IntegerField(db_index=True)
    subtype = models.IntegerField()
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # group can also act like user
    # remove and completely replace with permissions?
    group = models.ForeignKey(Group, db_index=True, blank=True, null=True, related_name='activities', help_text='To whom it may concern.')
    public = models.BooleanField(db_index=True, default=True)
    
    target_content_type = models.ForeignKey(ContentType, blank=True, related_name='target')
    target_id = models.IntegerField(blank=True)
    target = generic.GenericForeignKey('target_content_type', 'target_id')
    target_cache = models.CharField(max_length=250, blank=True)
    
    action_object_content_type = models.ForeignKey(ContentType, blank=True, related_name='action_object')
    action_object_id = models.IntegerField(blank=True)
    action_object = generic.GenericForeignKey('action_object_content_type', 'action_object_id')
    action_object_cache = models.CharField(max_length=250, blank=True)
    
    def A(self, model, text=None):
        if text is None:
            text = self.action_object_cache
        return u'<a href="%s/%d/">%s</a>' % (model, self.action_object_id, text)
        
    def T(self, model=None, text=None, url_extra=''):
        if model is None:
            model = self.target_content_type.model
        if text is None:
            text = self.target_cache
        return u'<a href="/%s/%d/%s">%s</a>' % (model, self.target_id, unicode(url_extra), text)
        
    def U(self):
        return u'<a href="/userprofile/%d/">%s</a>' % (self.actor_id, self.actor.get_full_name())
        
    def get_content(self):
        S = ''
        ttype = (self.type, self.subtype)
        if ttype in [TASK_ADD, SOLUTION_SUBMIT, SOLUTION_AS_SOLVED, SOLUTION_TODO, SOLUTION_AS_OFFICIAL]:
            S = self.T('task')
        if ttype == POST_SEND:
            S = self.T(url_extra='#post%d' % self.action_object_id, text=self.action_object_cache)
        return mark_safe(S)

    def get_label(self):
        if hasattr(self, '_label'):
            return self._label
        else:
            return action_label.get((self.type, self.subtype))
    
    def get_message(self):
        return getattr(self, '_message', u'')
