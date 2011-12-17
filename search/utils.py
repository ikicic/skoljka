from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.template.defaultfilters import slugify

from search.models import SearchCache, SearchCacheElement

from permissions.constants import VIEW
from task.models import Task

from taggit.models import Tag
from taggit.utils import parse_tags


def split_tags(tags):
    if type(tags) is unicode:
        tags = parse_tags(tags)
    if type(tags) is not list:
        tags = []
    return filter(None, [x.strip() for x in tags])


# recursive
# tags SHOULD be sorted (in order to do this efficiently)
def search_and_cache_tasks(tags, task_content_type):
    tag_string = u','.join(tags)
    try:
        cache = SearchCache.objects.get(tags=tag_string)
        return cache
    except:
        cache = SearchCache(tags=tag_string)
        cache.save()
        
# TODO: change to case-insensitive

    cached_tasks = Task.objects
    if len(tags) > 1:
        recursion = search_and_cache_tasks(tags[:-1], task_content_type)
        ids = SearchCacheElement.objects.filter(cache=recursion, content_type=task_content_type).values_list('object_id', flat=True)
        cached_tasks = cached_tasks.filter(id__in=ids)
    else:
        tag_object = Tag.objects.filter(name=tags[0])
        cached_tasks = cached_tasks.filter(tags=tag_object)

#    for task in cached_tasks:
#        element = SearchCacheElement(content_object=task, cache=cache)
#        element.save()
    query = 'INSERT INTO "search_searchcacheelement" ("object_id", "content_type_id", "cache_id")\
            SELECT "task_task"."id", %d, %d FROM "task_task" WHERE "task_task"."id" IN (%s)'        \
            % (task_content_type.id, cache.id, u','.join([str(x) for x in cached_tasks.values_list('id', flat=True)]))
    print query
    cursor = connection.cursor()
    cursor.execute(query)
    transaction.commit_unless_managed()

    print 'ubacio u hash za', tag_string
    return cache
    
def search_tasks(tags=[], none_if_blank=True, user=None, show_hidden=False):
    tags = split_tags(tags)
    if none_if_blank and not tags:
        return Task.objects.none()
    task_content_type = ContentType.objects.get_for_model(Task)

    if not tags:
        cache = None
    else:
        tags = sorted(tags)
        cache = search_and_cache_tasks(tags, task_content_type)

    if show_hidden:
        tasks = Task.objects.for_user(user, VIEW)
    else:
        tasks = Task.objects.filter(hidden=False)
    
    ids = SearchCacheElement.objects.filter(cache=cache, content_type=task_content_type).values_list('object_id', flat=True)
    
    return tasks.filter(id__in=ids)
