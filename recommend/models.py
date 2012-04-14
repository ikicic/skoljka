from django.db import models
from django.contrib.auth.models import User

from tags.models import Tag
from task.models import Task

from recommend.constants import *

from datetime import datetime
import math


class UserTagScore(models.Model):
    user = models.ForeignKey(User)
    tag = models.ForeignKey(Tag)
    
    interest = models.FloatField(default=0)
    variance = models.FloatField(default=0)
    mean = models.FloatField(default=0)
    last_update = models.DateTimeField(auto_now=True)

    cache_score = models.FloatField(default=0, db_index=True, help_text='Equals to interest * tag.weight, used for prefered tags for UserProfile')
    
    def get_interest(self):
        return self.interest * math.exp(INTEREST_TIME_FACTOR * (datetime.now() - self.last_update).total_seconds())

    def get_score(self, diff):
        return math.exp(-(diff - self.mean)**2 / (2 * self.variance))
    
    class Meta:
        unique_together = (('user', 'tag'),)



class UserRecommendation(models.Model):
    user = models.ForeignKey(User)
    task = models.ForeignKey(Task)
    score = models.FloatField(db_index=True, default=0)
    last_update = models.DateTimeField(db_index=True, auto_now=True)
    
    class Meta:
        unique_together = (('user', 'task'),)


# nuzno(?) da bi queryji koristili JOIN, a ne subqueryje
User.add_to_class('recommendations', models.ManyToManyField(Task, through=UserRecommendation))
