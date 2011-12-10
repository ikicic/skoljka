from django.db import models
from django.contrib.auth.models import User, Group
from django.utils.safestring import mark_safe

from mathcontent.models import MathContent


class UserGroup(models.Model):
    group = models.OneToOneField(Group, related_name='data')
    description = models.OneToOneField(MathContent)
    author = models.ForeignKey(User)
    date_created = models.DateTimeField(auto_now_add=True)

    member_count = models.IntegerField(default=0)
    
    def __unicode__(self):
        return mark_safe(u'[<a href="/usergroup/%d/">%s</a>]' % (self.pk, self.group.name))
    
    def get_users(self):
        return User.objects.filter(groups__pk=self.group.pk)
