from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.template.defaultfilters import slugify

from search.models import SearchCache, SearchCacheElement

from permissions.constants import VIEW
from task.models import Task

from taggit.models import Tag, TaggedItem
from taggit.utils import parse_tags


def split_tags(tags):
    if type(tags) is unicode:
        tags = parse_tags(tags)
    if type(tags) is not list:
        tags = []
    return filter(None, [x.strip() for x in tags])


# TODO: optimize!
# old_tags and new_tags are list of strings, not objects!
def update_search_cache(object, old_tags, new_tags):
    diff = set(new_tags) ^ set(old_tags)
    if not diff:
        return

    # this will delete SearchCacheElement rows as well
    SearchCache.objects.filter(tags__name__in=diff).delete()
    
    
    
# recursive
# tags SHOULD be sorted (in order to do this efficiently)
def search_and_cache(tags):
    tag_string = u','.join(tags)
    try:
        return SearchCache.objects.get(tag_string=tag_string)
    except:
        cache = SearchCache(tag_string=tag_string)
        cache.save()
        cache.tags.set(*tags)
        
    cache_content_type = ContentType.objects.get_for_model(SearchCache)
        
# TODO: change to case-insensitive

    cached_objects = TaggedItem.objects
    if len(tags) > 1:
        recursion = search_and_cache(tags[:-1])
        ids = SearchCacheElement.objects.filter(cache=recursion).values_list('object_id', flat=True)
        cached_objects = cached_objects.filter(object_id__in=ids)

    tag = Tag.objects.filter(name=tags[-1])
    # search shouldn't include itself
    cached_objects = cached_objects.filter(tag=tag).exclude(content_type=cache_content_type)

# TODO: replace this SELECT with cached_objects query
    query = 'INSERT INTO "search_searchcacheelement" ("object_id", "content_type_id", "cache_id")       \
            SELECT "object_id", "content_type_id", %d FROM "taggit_taggeditem" WHERE "id" IN (%s)' %    \
            (cache.id, ','.join((str(x) for x in cached_objects.values_list('id', flat=True))))
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
        cache = search_and_cache(tags)

    if show_hidden:
        tasks = Task.objects.for_user(user, VIEW)
    else:
        tasks = Task.objects.filter(hidden=False)
    
    ids = SearchCacheElement.objects.filter(cache=cache, content_type=task_content_type).values_list('object_id', flat=True)
    
    return tasks.filter(id__in=ids).distinct()
