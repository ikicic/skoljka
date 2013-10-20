from django.contrib.auth.models import User
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from mathcontent.models import MathContent
from mathcontent.forms import MathContentForm

class Post(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()

    author = models.ForeignKey(User)
    content = models.OneToOneField(MathContent)
    date_created = models.DateTimeField(auto_now_add=True)
    last_edit_by = models.ForeignKey(User, related_name='+')
    last_edit_time = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'Post #{}'.format(self.id)

    def can_edit(self, user, container=None):
        if container is None:
            container = self.content_object
        return user.is_superuser            \
            or self.author_id == user.id    \
            or hasattr(container, "author_id") and container.author_id == user.id
