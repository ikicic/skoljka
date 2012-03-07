from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.db.models import Count
from django.template.defaultfilters import slugify

from search.models import SearchCache, SearchCacheElement

from permissions.constants import VIEW
from task.models import Task

from tags.models import Tag, TaggedItem
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
    
    

# TODO: fix case-sensitivity bug    
# recursive
# tags SHOULD be sorted (in order to do this efficiently)
def search_and_cache(tags):
    tag_string = u','.join(tags)
    try:
        return SearchCache.objects.get(tag_string=tag_string)
    except:
        cache = SearchCache(tag_string=tag_string)
        cache.save()
        # TODO: this line makes trouble
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
    ids = cached_objects.values_list('id', flat=True)
    
    if not ids:         # MySQL doesn't like WHERE ... IN with empty list
        return cache
        
# TODO: replace this SELECT with cached_objects query
    query = 'INSERT INTO search_searchcacheelement (object_id, content_type_id, cache_id)   \
            SELECT object_id, content_type_id, %d FROM tags_taggeditem WHERE id IN (%s)' %  \
            (cache.id, ','.join([str(x) for x in ids]))
    print query

    cursor = connection.cursor()
    cursor.execute(query)
    transaction.commit_unless_managed()

    #print 'ubacio u hash za', tag_string
    return cache


# none_if_blank? zasto bi to bio posao ove funkcije
def search_tasks(tags=[], none_if_blank=True, user=None, **kwargs):
    tags = split_tags(tags)
    if none_if_blank and not tags:
        return Task.objects.none()
    task_content_type = ContentType.objects.get_for_model(Task)

    if kwargs.get('show_hidden'):
        tasks = Task.objects.for_user(user, VIEW).distinct()
    else:
        tasks = Task.objects.filter(hidden=False).distinct()

    if tags:
        tags = sorted(tags)
        cache = search_and_cache(tags)
        ids = SearchCacheElement.objects.filter(cache=cache, content_type=task_content_type).values_list('object_id', flat=True)
        tasks = tasks.filter(id__in=ids)

    if kwargs.get('quality_min') is not None: tasks = tasks.filter(quality_rating_avg__gte=kwargs['quality_min'])
    if kwargs.get('quality_max') is not None: tasks = tasks.filter(quality_rating_avg__lte=kwargs['quality_max'])
    if kwargs.get('difficulty_min') is not None: tasks = tasks.filter(difficulty_rating_avg__gte=kwargs['difficulty_min'])
    if kwargs.get('difficulty_max') is not None: tasks = tasks.filter(difficulty_rating_avg__lte=kwargs['difficulty_max'])

    # TODO: perm
    if kwargs.get('groups'):
        ids = ','.join([str(x) for x in tasks.values_list('id', flat=True)])
        group_ids = ','.join([str(x.id) for x in kwargs['groups']])
        tasks = Task.objects.raw(
            'SELECT A.id, A.hidden, A.name, A.solved_count, A.quality_rating_avg, A.difficulty_rating_avg, COUNT(DISTINCT B.id) AS search_solved_count FROM task_task AS A \
                LEFT JOIN solution_solution AS B ON (B.task_id = A.id) \
                LEFT JOIN auth_user_groups AS C ON (C.user_id = B.author_id AND C.group_id IN (%s)) \
                WHERE A.id IN (%s) \
                GROUP BY A.id' % (group_ids, ids)
            )

        tasks = list(tasks)
    
    return tasks
