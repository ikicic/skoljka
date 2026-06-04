import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import get_valid_filename
from django.utils.translation import get_language

from skoljka.apps.tags.models import Tag
from skoljka.utils.permissions import PermissionModel


class Source(PermissionModel):
    slug = models.SlugField(unique=True)
    parent_id: int | None
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    order = models.IntegerField(default=0)
    tags = models.ManyToManyField(Tag, blank=True)
    translations = models.JSONField(default=dict)
    # {"en": {"name": "IMO", "description": "...", "url": "https://..."}, "hr": {...}}

    class Meta:
        ordering = ["order", "slug"]

    def _language(self, language: str | None = None) -> str:
        return (language or get_language() or "en").split("-")[0]

    def name(self, language: str | None = None) -> str:
        language = self._language(language)
        tr = self.translations.get(language, self.translations.get("en", {}))
        return tr.get("name", self.slug)

    def __str__(self) -> str:
        return self.name()

    def get_absolute_url(self) -> str:
        return reverse("source_detail", kwargs={"slug": self.slug})


def source_document_upload_to(instance: "SourceDocument", filename: str) -> str:
    filename = get_valid_filename(filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])
    return f"documents/{uuid.uuid4()}/{filename or 'document'}"


class SourceDocument(models.Model):
    class Kind(models.TextChoices):
        PROBLEMS = "problems", "Problems"
        SOLUTIONS = "solutions", "Solutions"
        OTHER = "other", "Other"

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="documents")
    year = models.IntegerField(null=True, blank=True)
    language = models.CharField(max_length=10, blank=True)
    kind = models.CharField(max_length=32, choices=Kind.choices, default=Kind.PROBLEMS)
    title = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to=source_document_upload_to)
    original_filename = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [models.F("year").desc(nulls_last=True), "original_filename", "id"]

    def label(self) -> str:
        if self.title:
            return self.title
        if self.original_filename:
            return self.original_filename
        return self.get_kind_display()
