from django.db.models.signals import post_save
from django.dispatch import receiver

from skoljka.apps.accounts.models import User


@receiver(post_save, sender=User)
def create_personal_group(sender, instance: User, created: bool, **kwargs) -> None:
    if created:
        instance.ensure_personal_group()
