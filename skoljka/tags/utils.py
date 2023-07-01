from django.contrib.contenttypes.models import ContentType
from django.utils.html import mark_safe
from taggit.utils import parse_tags

from skoljka.tags.models import Tag, TaggedItem
from skoljka.tags.signals import (
    object_tag_ids_changed,
    object_tag_ids_changed_high_priority,
)

# TODO: Taggit is case sensitive, and makes different slugs for tags that
# differ in case only. We want tags to be case-insensitive, so we use a wrapper.
# Therefore, we can stop to use Taggit and use our own model that has no slug
# field. Before making any changes, find a way to make tags multilingual.


def _set_tag_ids(instance, content_type, old_tag_ids, new_tag_ids):
    """
    Sets tags (a list or a string of comma-separated tags) for the given
    object.

    Returns the difference in number of tags now and before.
    """
    if not content_type:
        content_type = ContentType.objects.get_for_model(instance)

    old_tag_ids = set(old_tag_ids)
    new_tag_ids = set(new_tag_ids)

    added = 0
    removed = 0
    for tag_id in old_tag_ids - new_tag_ids:
        tagged_item = TaggedItem.objects.get(
            object_id=instance.id, content_type=content_type, tag_id=tag_id
        )
        tagged_item.delete()
        removed += 1

    for tag_id in new_tag_ids - old_tag_ids:
        TaggedItem.objects.create(
            object_id=instance.id, content_type=content_type, tag_id=tag_id
        )
        added += 1

    if added + removed > 0:
        if hasattr(instance, '_cache_tagged_items'):
            delattr(instance, '_cache_tagged_items')
        object_tag_ids_changed_high_priority.send(
            sender=content_type.model_class(),
            instance=instance,
            old_tag_ids=old_tag_ids,
            new_tag_ids=new_tag_ids,
        )
        object_tag_ids_changed.send(
            sender=content_type.model_class(),
            instance=instance,
            old_tag_ids=old_tag_ids,
            new_tag_ids=new_tag_ids,
        )

    return added - removed


def set_tags(instance, tags, content_type=None):
    old_tag_ids = list(instance.tags.values_list('id', flat=True))
    new_tag_ids = tag_names_to_ids(tags, add=True)
    return _set_tag_ids(instance, content_type, old_tag_ids, new_tag_ids)


def add_tags(instance, tags, content_type=None):
    old_tag_ids = list(instance.tags.values_list('id', flat=True))
    new_tag_ids = old_tag_ids + tag_names_to_ids(tags, add=True)
    return _set_tag_ids(instance, content_type, old_tag_ids, new_tag_ids)


def remove_tags(instance, tags_to_remove, content_type=None):
    old_tag_ids = set(instance.tags.values_list('id', flat=True))
    to_remove = tag_names_to_ids(tags_to_remove)
    new_tag_ids = old_tag_ids - set(to_remove)
    return _set_tag_ids(instance, content_type, old_tag_ids, new_tag_ids)


def split_tags(tags):
    """
    Split tags. Not necessarily sorted!
    """
    if tags is None:
        return []
    if isinstance(tags, basestring):
        # Force comma between tags. If no commas are given, assume one multiword
        # tag is given.
        tags = parse_tags(tags if ',' in tags else '"%s"' % tags)
    if not isinstance(tags, list):
        raise ValueError("split_tags accepts a string, list or None only!")
    # Using split+join to remove multiple whitespace and strip.
    return filter(None, [' '.join(x.split()) for x in tags])


def split_tag_ids(tag_ids):
    """
    Split comma-separated ids from the tag_ids string and returns a list of ids.
    If given a list, returns with no changes.
    Doesn't sort or remove duplicates.
    """
    if isinstance(tag_ids, list):
        return tag_ids
    return [int(x) for x in tag_ids.split(',')]


def get_available_tags(tags):
    """
    Get the list of tag names and returns existing tags queryset.
    Does not preserve the order of tags. Removes duplicates.

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
    Fix cases for known tags and keep unknown tags.
    Doesn't have to preserve order or remove duplicates.
    Returns a list of tag names.
    """
    tags = split_tags(tags)
    available = list(get_available_tags(tags).values_list('name', flat=True))
    lowercase = {x.lower(): x for x in available}

    # If it exists, return original tag name. Otherwise, use as it is written.
    return [lowercase.get(y.lower(), y) for y in tags]


def tag_names_to_ids(tag_names, add=False):
    """
    Search tags by their names. If add is set to True and a name is not found,
    a new tag is added. Otherwise, it is ignored.
    Does not preserve order!
    """
    if add:
        tag_names = split_tags(tag_names)
        available = Tag.objects.filter(name__in=tag_names).values_list('id', 'name')
        lowercase = {name.lower(): tag_id for tag_id, name in available}
        result = []
        for name in tag_names:
            if name.lower() in lowercase:
                result.append(lowercase[name.lower()])
            else:
                tag = Tag(name=name)
                tag.save()
                result.append(tag.id)
        return result
    else:
        return Tag.objects.filter(name__in=split_tags(tag_names)).values_list(
            'id', flat=True
        )


def get_object_tagged_items(instance):
    """Returns TaggedItem objects linked to a given object."""
    if not hasattr(instance, '_cache_tagged_items'):
        content_type = ContentType.objects.get_for_model(instance)

        # Get all tags (TaggedItem)
        queryset = TaggedItem.objects.filter(
            content_type=content_type, object_id=instance.id
        ).select_related('tag')

        # Evaluate and sort by tag.name
        instance._cache_tagged_items = sorted(queryset, key=lambda x: x.tag.name)

    return instance._cache_tagged_items
