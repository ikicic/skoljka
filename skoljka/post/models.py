from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

from skoljka.mathcontent.models import MathContent


class Post(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()

    author = models.ForeignKey(User)
    content = models.OneToOneField(MathContent)
    date_created = models.DateTimeField(auto_now_add=True)
    last_edit_by = models.ForeignKey(User, related_name='+')
    last_edit_time = models.DateTimeField(auto_now=True)

    # Used to attached extra information to a post. Intentionally an Integer,
    # in order to add constant size to the field (not to increase its
    # complexity much). To allow for counting, a db index (content_type_id,
    # object_id, extra) should be included in the database.
    extra = models.IntegerField(
        default=0, help_text="Application-specific additional information."
    )

    def __unicode__(self):
        return u'Post #{}'.format(self.id)

    def can_edit(self, user, container=None):
        if container is None:
            container = self.content_object
        return (
            user.is_superuser
            or self.author_id == user.id
            or hasattr(container, "author_id")
            and container.author_id == user.id
        )
