from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.utils.safestring import mark_safe

from mathcontent.models import MathContent
from permissions.models import PerObjectGroupPermission
#from permissions.models import PerObjectUserPermission
from post.generic import PostGenericRelation
from rating.fields import RatingField
from taggit.managers import TaggableManager

from rating.constants import *

# TODO: rename "author" to "added_by" (or add another column "added_by")
# TODO: rename "name" to "title"

class TaskPermissionManager(models.Manager):
    def for_user(self, user, permission_type):
        if user is not None and user.is_authenticated():
            # yeah, right...
            return self.filter(
                  Q(hidden=False)
                | Q(author=user)
#                | Q(user_permissions__user=user, user_permissions__permission_type=permission_type)
                | Q(group_permissions__group__user=user, group_permissions__permission_type=permission_type))
        else:
            return self.filter(hidden=False)


class Task(models.Model):
    name = models.CharField(max_length=200)
    content = models.OneToOneField(MathContent)
    author = models.ForeignKey(User)
    date_created = models.DateTimeField(auto_now_add=True)
    hidden = models.BooleanField(default=False)
    
#    user_permissions = generic.GenericRelation(PerObjectUserPermission)
    group_permissions = generic.GenericRelation(PerObjectGroupPermission)
    posts = PostGenericRelation()
    tags = TaggableManager(blank=True)
    quality_rating = RatingField(**QUALITY_RATING_ATTRS)
    difficulty_rating = RatingField(**DIFFICULTY_RATING_ATTRS)

    solved_count = models.IntegerField(default=0)
    
    objects = TaskPermissionManager()

    class Meta:
        ordering = ['id']
    
    def __unicode__(self):
        return self.name
