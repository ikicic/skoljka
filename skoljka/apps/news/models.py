from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from skoljka.apps.content.models import Content


class NewsPost(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    hidden = models.BooleanField(default=True)
    created_by_id: int | None
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="news_posts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    content = GenericRelation(Content)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
