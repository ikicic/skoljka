from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

from skoljka.tags.managers import TaggableManager


def _normal_search_key(tag_ids):
    return 'N' + ','.join([str(id) for id in tag_ids])


def _reverse_search_key(tag_ids):
    return 'R' + ','.join([str(id) for id in tag_ids])


class SearchCache(models.Model):
    key = models.CharField(max_length=100, unique=True)
    tags = TaggableManager()


class SearchCacheElement(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()

    cache = models.ForeignKey(SearchCache, related_name='result')
