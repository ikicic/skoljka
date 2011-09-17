from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class Task(models.Model):
    name = models.CharField(max_length=200)
    content = models.CharField(max_length=2000)
    author = models.ForeignKey(User)
    