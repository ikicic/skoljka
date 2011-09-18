from django.contrib.auth.models import User
from django.db import models
from mathcontent.models import MathContent

class Task(models.Model):
    name = models.CharField(max_length=200)
    content = models.OneToOneField(MathContent)
    author = models.ForeignKey(User)    
