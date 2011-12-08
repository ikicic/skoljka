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
