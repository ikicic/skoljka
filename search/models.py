from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from tags.managers import TaggableManager

def _normal_search_key(tags):
    return 'N' + ','.join([str(tag.id) for tag in tags])

def _reverse_search_key(tags):
    return 'R' + ','.join([str(tag.id) for tag in tags])

class SearchCache(models.Model):
    key = models.CharField(max_length=100, unique=True)
    tags = TaggableManager()


class SearchCacheElement(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()
    
    cache = models.ForeignKey(SearchCache, related_name='result')

