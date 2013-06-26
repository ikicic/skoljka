from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.db.models import Count
from django.template.defaultfilters import slugify

import johnny.cache

from permissions.constants import VIEW
from solution.models import STATUS
from task.models import Task
from tags.models import Tag, TaggedItem
from tags.utils import get_available_tags, replace_with_original_tags,  \
    split_tags, split_tag_ids

from search.models import SearchCache, SearchCacheElement, _normal_search_key, \
    _reverse_search_key

from collections import defaultdict


# TODO: optimize!
# old_tags and new_tags are list of strings, not objects!
def update_search_cache(object, old_tags, new_tags):
    diff = set(new_tags) ^ set(old_tags)
    if not diff:
        return

    # this will delete SearchCacheElement rows as well
    SearchCache.objects.filter(tags__name__in=diff).delete()


# recursive
def _search_and_cache(tag_ids):
    """
        Arguments:
            tag_ids == list of Tag IDs

        Note:
            To make this method more efficient, tags should be sorted by some
            of its attributes (e.g. by id itself).
    """
    key = _normal_search_key(tag_ids)
    try:
        return SearchCache.objects.get(key=key)
    except:
        cache = SearchCache(key=key)
        cache.save()
        tags = Tag.objects.filter(id__in=tag_ids)
        cache.tags.set(*tags)

    cache_content_type = ContentType.objects.get_for_model(SearchCache)

    tag_id = tag_ids[-1]
    if len(tag_ids) > 1:
        recursion = _search_and_cache(tag_ids[:-1])
        query = 'INSERT INTO search_searchcacheelement (object_id, content_type_id, cache_id)'  \
                ' SELECT A.object_id, A.content_type_id, %d FROM search_searchcacheelement AS A'    \
                ' INNER JOIN tags_taggeditem AS B ON (A.object_id = B.object_id AND A.content_type_id = B.content_type_id)' \
                ' WHERE A.cache_id=%d AND B.tag_id=%d;' \
                % (cache.id, recursion.id, tag_id)
    else:
        # search shouldn't include itself
        query = 'INSERT INTO search_searchcacheelement (object_id, content_type_id, cache_id)'  \
                ' SELECT A.object_id, A.content_type_id, %d FROM tags_taggeditem AS A'  \
                ' WHERE A.tag_id=%d AND A.content_type_id != %d;'   \
                % (cache.id, tag_id, cache_content_type.id)

    cursor = connection.cursor()
    cursor.execute(query)
    transaction.commit_unless_managed()

    johnny.cache.invalidate('search_searchcacheelement')

    return cache


def search(tags=None, tag_ids=None):
    """
        Find all objects whose tags make superset of given tags.

        If any unknown tag given or none tags given at all, returns None.
        Otherwise, returns SearchCache object.
    """
    if tags:
        tags = split_tags(tags)
        if not tags:
            return None # if no tag given, don't just return all objects

        # what if an unknown tag is in the list?
        tag_ids = list(get_available_tags(tags).values_list('id', flat=True))

        if len(tag_ids) != len(tags):
            return None # unknown tag given
    elif not tag_ids:
        return None
    else:
        tag_ids = split_tag_ids(tag_ids)

    # Sort by id before calling.
    return _search_and_cache(sorted(tag_ids))

def search_tasks(tags=[], tag_ids=None, user=None, **kwargs):
    if kwargs.get('no_hidden_check'):
        tasks = Task.objects.all()
    elif kwargs.get('show_hidden'):
        tasks = Task.objects.for_user(user, VIEW).distinct()
    else:
        tasks = Task.objects.filter(hidden=False)

    cache = search(tags=tags, tag_ids=tag_ids)
    if not cache:
        return Task.objects.none()

    tasks = tasks.filter(search_cache_elements__cache=cache)

    filters = {}
    if kwargs.get('quality_min') is not None:
        filters['quality_rating_avg__gte'] = kwargs['quality_min']
    if kwargs.get('quality_max') is not None:
        filters['quality_rating_avg__lte'] = kwargs['quality_max']
    if kwargs.get('difficulty_min') is not None:
        filters['difficulty_rating_avg__gte'] = kwargs['difficulty_min']
    if kwargs.get('difficulty_max') is not None:
        filters['difficulty_rating_avg__lte'] =kwargs['difficulty_max']

    if filters:
        tasks = tasks.filter(**filters)

    if kwargs.get('groups'):
        ids = ','.join([str(x) for x in tasks.values_list('id', flat=True)])
        group_ids = ','.join([str(x.id) for x in kwargs['groups']])
        statuses = '%d,%d' % (STATUS['as_solved'], STATUS['submitted'])

        # TODO: can this be optimized? use SearchCache instead of IN?
        tasks = Task.objects.raw(
            'SELECT T.*, COUNT(DISTINCT S.id) AS search_solved_count FROM task_task AS T'
                ' INNER JOIN solution_solution AS S ON (S.task_id = T.id)'
                ' INNER JOIN auth_user_groups AS UG ON (UG.user_id = S.author_id AND UG.group_id IN (%s))'
                ' WHERE T.id IN (%s) AND S.status IN (%s)'
                ' GROUP BY T.id' % (group_ids, ids, statuses)
            )

        tasks = list(tasks)

    return tasks

def reverse_search(input):
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
    input = split_tags(input)
    if not input:
        return None # if no tag given, don't just return all objects

    tags = get_available_tags(input)
    if len(tags) != len(input):
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

    # Filter only those objects whose tags are subset of the given set of tags
    SearchCacheElement.objects.bulk_create(
        SearchCacheElement(object_id=key[0], content_type_id=key[1], cache=cache)
        for key, obj_tags in objects.iteritems()
        if obj_tags.issubset(ids_set)
    )

    return cache
