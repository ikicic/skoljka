from django.db import models
from django.contrib.auth.models import User
from task.models import Task
from mathcontent.models import MathContent


# Create your models here.

class Solution(models.Model):
    task = models.ForeignKey(Task)
    author = models.ForeignKey(User)
    content = models.ForeignKey(MathContent)
