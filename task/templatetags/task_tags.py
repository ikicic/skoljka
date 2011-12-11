from django import template
from django.contrib.contenttypes.models import ContentType

from taggit.models import TaggedItem
from taggit.utils import parse_tags

import collections

register = template.Library()

@register.filter
def cache_task_tags(tasks):
    task_content_type = ContentType.objects.get_by_natural_key(app_label="task", model="task")
    ids = [x.id for x in tasks]
    tagovi = TaggedItem.objects.filter(content_type=task_content_type, object_id__in=ids).select_related('tag')
    tags = collections.defaultdict(list)
    for x in tagovi:
        tags[x.object_id].append(x.tag.name)
        
    for task in tasks:
        task._cache_tag_set = sorted(tags[task.id])
        
    return tasks
