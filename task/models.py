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

QUALITY_RATING_TITLES = [u'Loš. Dosadan.', u'Ima i boljih.', u'Dobar zadatak.', u'Jako dobar. Zanimljiv.', u'Izvrstan. Vrlo zanimljiv.']
DIFFICULTY_RATING_TITLES = [u'OŠ lakši', u'OŠ teži', u'SŠ lakši', u'SŠ teži', u'Srednje težine',
    u'Shortlist 1/2', u'Shortlist 3/4', u'Shortlist 5/6', u'Shortlist 7/8', u'Nerješiv']

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
    quality_rating = RatingField(titles=QUALITY_RATING_TITLES)
    difficulty_rating = RatingField(range=10, titles=DIFFICULTY_RATING_TITLES)

    solved_count = models.IntegerField(default=0)
    
    objects = TaskPermissionManager()

    class Meta:
        ordering = ['id']
    
    def __unicode__(self):
        return self.name
