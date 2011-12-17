from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

class SearchCache(models.Model):
    tags = models.CharField(max_length=100, unique=True)
    

class SearchCacheElement(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()
    
    cache = models.ForeignKey(SearchCache, related_name='result')

