from django.contrib.contenttypes.models import ContentType

from taggit.utils import parse_tags

from tags.models import Tag, TaggedItem

def add_task_tags(tags, task, content_type=None):
    """
    Adds given tags (a list or a string of comma-separated tags) to the given
    task. Returns the total number of new tags added (number of new TaggedItem
    instances).
    """
    from tags.signals import send_task_tags_changed_signal
    if not content_type:
        content_type = ContentType.objects.get_for_model(task)

    total_created = 0
    old_tags = list(task.tags.values_list('name', flat=True))
    for tag in split_tags(tags):
        # https://code.djangoproject.com/ticket/13492
        # (mozda vezana rasprava: https://code.djangoproject.com/ticket/7789)
        try:
            tag = Tag.objects.get(name__iexact=tag)
        except Tag.DoesNotExist:
            tag = Tag.objects.create(name=tag)

        taggeditem, created = TaggedItem.objects.get_or_create(
                object_id=task.id, content_type=content_type, tag=tag)
        if created:
            total_created += 1

    if total_created:
        new_tags = task.tags.values_list('name', flat=True)
        send_task_tags_changed_signal(task, old_tags, new_tags)

    return total_created


def split_tags(tags):
    if isinstance(tags, basestring):
        # Force comma between tags. If no commas are given, assume one multiword
        # tag is given.
        tags = parse_tags(tags if ',' in tags else '"%s"' % tags)
    if not isinstance(tags, list):
        tags = []
    return filter(None, [x.strip() for x in tags])

def split_tag_ids(tag_ids):
    if isinstance(tag_ids, list):
        return tag_ids
    return [int(x) for x in tag_ids.split(',')]

def get_available_tags(tags):
    """
        Get the list of tag names and returns existing tags queryset.
        Does not preserve the order of tags.

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
    # TODO: strictly define if `tags` is a string or a list
    tags = split_tags(tags)
    available = list(get_available_tags(tags).values_list('name', flat=True))
    lowercase = {x.lower(): x for x in available}

    # If it exists, return original tag name. Otherwise, use as it is written.
    return [lowercase.get(y.lower(), y) for y in tags]


def get_object_tagged_items(instance):
    if not hasattr(instance, '_cache_tagged_items'):
        content_type = ContentType.objects.get_for_model(instance)

        # Get all tags (TaggedItem)
        queryset = TaggedItem.objects   \
            .filter(content_type=content_type, object_id=instance.id)   \
            .select_related('tag')

        # Evaluate and sort by (tag.name, votes_sum)
        instance._cache_tagged_items = \
            sorted(queryset, key=lambda x: (x.tag.name, x.votes_sum))

    return instance._cache_tagged_items
