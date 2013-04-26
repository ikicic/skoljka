from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.db.models import Count
from django.template.defaultfilters import slugify

import johnny.cache
from taggit.utils import parse_tags

from permissions.constants import VIEW
from task.models import Task
from tags.models import Tag, TaggedItem

from search.models import SearchCache, SearchCacheElement, _normal_search_key, \
    _reverse_search_key

from collections import defaultdict

def split_tags(tags):
    if type(tags) is unicode:
        tags = parse_tags(tags)
    if type(tags) is not list:
        tags = []
    return filter(None, [x.strip() for x in tags])

def get_available_tags(tags):
    """
        Get the list of tag names and returns existing tags queryset.
        Note that the order of tags might not be preserved.

        Argument:
            list or tag names, comma-separated string of tags...
            (Passes the argument to split_tags)

        Example:
        tags = get_available_tags(['Memo', 'GEO', '2007', 'unknown_tag'])
        tags.values_list('name', flat=True)
        --> ['geo', 'MEMO', '2007']
    """

    return Tag.objects.filter(name__in=split_tags(tags))

def replace_with_original_tags(tags):
    """
        Search for existing tags and fix cases.
    """
    available = list(get_available_tags(tags).values_list('name', flat=True))
    lowercase = {x.lower(): x for x in available}

    # If it exists, return original tag name. Otherwise, use as it is written.
    return [lowercase.get(y.lower(), y) for y in tags]



# TODO: optimize!
# old_tags and new_tags are list of strings, not objects!
def update_search_cache(object, old_tags, new_tags):
    diff = set(new_tags) ^ set(old_tags)
    if not diff:
        return

    # this will delete SearchCacheElement rows as well
    SearchCache.objects.filter(tags__name__in=diff).delete()



# recursive
def _search_and_cache(tags):
    """
        Arguments:
            tags == list of Tag instances

        Note:
            To make this method more efficient, tags should be sorted by some
            of its attributes (e.g. id).
    """
    key = _normal_search_key(tags)
    try:
        return SearchCache.objects.get(key=key)
    except:
        cache = SearchCache(key=key)
        cache.save()
        cache.tags.set(*tags)

    cache_content_type = ContentType.objects.get_for_model(SearchCache)

    tag = tags[-1]
    if len(tags) > 1:
        recursion = _search_and_cache(tags[:-1])
        query = 'INSERT INTO search_searchcacheelement (object_id, content_type_id, cache_id)'  \
                ' SELECT A.object_id, A.content_type_id, %d FROM search_searchcacheelement AS A'    \
                ' INNER JOIN tags_taggeditem AS B ON (A.object_id = B.object_id AND A.content_type_id = B.content_type_id)' \
                ' WHERE A.cache_id=%d AND B.tag_id=%d;' \
                % (cache.id, recursion.id, tag.id)
    else:
        # search shouldn't include itself
        query = 'INSERT INTO search_searchcacheelement (object_id, content_type_id, cache_id)'  \
                ' SELECT A.object_id, A.content_type_id, %d FROM tags_taggeditem AS A'  \
                ' WHERE A.tag_id=%d AND A.content_type_id != %d;'   \
                % (cache.id, tag.id, cache_content_type.id)

    cursor = connection.cursor()
    cursor.execute(query)
    transaction.commit_unless_managed()

    johnny.cache.invalidate('search_searchcacheelement')

    return cache

"""
from johnny.signals import qc_hit, qc_miss
from django.dispatch import receiver
@receiver(qc_hit)
def _hit(sender, **kwargs):
    print 'HIT', sender, kwargs

@receiver(qc_miss)
def _miss(sender, **kwargs):
    print 'MISS', sender, kwargs
"""

def search(tags):
    """
        Find all objects whose tags make superset of given tags.

        Note: Unknown tags are ignored.

        Returns SearchCache object if any (existing) tag given, otherwise None.
    """

    # what if an unknown tag is in the list?
    tags = get_available_tags(tags)

    # Sort before calling. (tag order does not matter, but it makes search
    # more efficient)
    tags = sorted(tags, key=lambda x: x.id)

    return _search_and_cache(tags) if tags else None

# none_if_blank? zasto bi to bio posao ove funkcije
def search_tasks(tags=[], none_if_blank=True, user=None, **kwargs):
    # TODO: remove none_if_blank parameter!

    if kwargs.get('no_hidden_check'):
        tasks = Task.objects.all()
    elif kwargs.get('show_hidden'):
        tasks = Task.objects.for_user(user, VIEW).distinct()
    else:
        tasks = Task.objects.filter(hidden=False)

    tags = split_tags(tags)
    if none_if_blank and not tags:
        return Task.objects.none()

    cache = search(tags)
    if cache:
        tasks = tasks.filter(search_cache_elements__cache=cache)

    if kwargs.get('quality_min') is not None: tasks = tasks.filter(quality_rating_avg__gte=kwargs['quality_min'])
    if kwargs.get('quality_max') is not None: tasks = tasks.filter(quality_rating_avg__lte=kwargs['quality_max'])
    if kwargs.get('difficulty_min') is not None: tasks = tasks.filter(difficulty_rating_avg__gte=kwargs['difficulty_min'])
    if kwargs.get('difficulty_max') is not None: tasks = tasks.filter(difficulty_rating_avg__lte=kwargs['difficulty_max'])

    # TODO: perm
    if kwargs.get('groups'):
        ids = ','.join([str(x) for x in tasks.values_list('id', flat=True)])
        group_ids = ','.join([str(x.id) for x in kwargs['groups']])

        # TODO: ispitati treba li LEFT ili INNER JOIN
        # FIXME: why just these columns?
        tasks = Task.objects.raw(
            'SELECT A.id, A.hidden, A.name, A.solved_count, A.quality_rating_avg, A.difficulty_rating_avg, COUNT(DISTINCT B.id) AS search_solved_count FROM task_task AS A \
                LEFT JOIN solution_solution AS B ON (B.task_id = A.id) \
                LEFT JOIN auth_user_groups AS C ON (C.user_id = B.author_id AND C.group_id IN (%s)) \
                WHERE A.id IN (%s) \
                GROUP BY A.id' % (group_ids, ids)
            )

        tasks = list(tasks)

    return tasks

def reverse_search(tags):
    """
        Find all objects whose tags are a subset of given tags.

        Returns SearchCache object if any (existing) tag given, otherwise None.

        Example:
            reverse_search(['imo', '1997'])
            --> SearchCache pointing to:
                --> Folder with filter tag 'imo'
                --> Folder with filter tag 'imo', '1997'
                (...)

            Examples of non matching objects:
            --> Folder with filter tag 'shortlist', '1997'
            --> Task with tags 'imo', '1997', 'geo'
    """
    tags = get_available_tags(tags)
    if len(tags) == 0:
        return None

    key = _reverse_search_key(tags)

    try:
        return SearchCache.objects.get(key=key)
    except SearchCache.DoesNotExist:
        pass

    # Create cache object.
    cache = SearchCache(key=key)
    cache.save()
    cache.tags.set(*tags)

    # Generate SQL query
    cache_content_type = ContentType.objects.get_for_model(SearchCache)
    tag_ids = [x.id for x in tags]
    query = 'SELECT DISTINCT A.object_id, A.content_type_id, A.tag_id FROM tags_taggeditem A' \
            '   INNER JOIN tags_taggeditem B'   \
            '       ON (A.object_id = B.object_id AND A.content_type_id = B.content_type_id)'   \
            '   WHERE B.tag_id IN (%s) AND B.content_type_id != %d' \
        % (','.join([str(id) for id in tag_ids]), cache_content_type.id)

    # Manually fetch.
    cursor = connection.cursor()
    cursor.execute(query)
    tagged_items = cursor.fetchall()


    # Generate and save search result.
    objects = defaultdict(set)
    for object_id, content_type_id, tag_id in tagged_items:
        # Seperate tagged items by objects (get tags for each object)
        objects[(object_id, content_type_id)].add(tag_id)

    ids_set = set(tag_ids)

    # Filter only those objects whose tags are subset of given set of tags
    SearchCacheElement.objects.bulk_create([
        SearchCacheElement(object_id=key[0], content_type_id=key[1], cache=cache)
        for key, obj_tags in objects.iteritems()
        if obj_tags.issubset(ids_set)])

    return cache
