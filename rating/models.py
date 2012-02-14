from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Vote(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()

    key = models.CharField(max_length=32)
    user = models.ForeignKey(User)

    value = models.IntegerField()
    date = models.DateTimeField(auto_now=True)

    
# strpati object_id, content_type i key u jedan key?
class Score(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()
    
    # single object can have different scores (types)
    key = models.CharField(max_length=32)
    
    sum = models.IntegerField(default=0)
    count = models.IntegerField(default=0)
    # distribution = models.CommaSeperatedIntegerField()
    
    class Meta:
        unique_together = (('object_id', 'content_type', 'key'),)
    