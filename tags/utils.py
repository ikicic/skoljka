from django.contrib.contenttypes.models import ContentType

from tags.models import TaggedItem

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
