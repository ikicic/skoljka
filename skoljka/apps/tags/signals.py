from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from skoljka.apps.tags.cache import clear_tag_api_cache
from skoljka.apps.tags.models import Tag


@receiver([post_save, post_delete], sender=Tag)
def invalidate_tag_api_cache(**kwargs):
    clear_tag_api_cache()
