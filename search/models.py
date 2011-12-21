from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from taggit.managers import TaggableManager

class SearchCache(models.Model):
    tag_string = models.CharField(max_length=100, unique=True)
    tags = TaggableManager()


class SearchCacheElement(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()
    
    cache = models.ForeignKey(SearchCache, related_name='result')

