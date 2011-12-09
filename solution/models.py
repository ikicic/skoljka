from django.db import models
from django.contrib.auth.models import User

from mathcontent.models import MathContent
from post.generic import PostGenericRelation
from task.models import Task

class Solution(models.Model):
    task = models.ForeignKey(Task)
    author = models.ForeignKey(User)
    content = models.OneToOneField(MathContent)
    date_created = models.DateTimeField(auto_now_add=True)
    posts = PostGenericRelation()
    