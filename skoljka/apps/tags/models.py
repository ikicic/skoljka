from django.db import models
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.http import urlencode


class Tag(models.Model):
    id: int

    class Kind(models.TextChoices):
        TOPIC = "topic"
        TECHNIQUE = "technique"
        META = "meta"

    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    parent_id: int | None
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    hidden = models.BooleanField(default=False)
    translations = models.JSONField(default=dict)
    # {"en": "Algebra", "hr": "Algebra"}
    short_translations = models.JSONField(default=dict, blank=True)
    # {"en": "3D", "hr": "3D"}
    descriptions = models.JSONField(default=dict, blank=True)
    # {"en": "Problems about equations...", "hr": "Zadaci o jednadžbama..."}

    class Meta:
        ordering = ["slug"]

    def _language(self, language: str | None = None) -> str:
        return (language or get_language() or "en").split("-")[0]

    def name(self, language: str | None = None) -> str:
        language = self._language(language)
        return self.translations.get(language, self.translations.get("en", self.slug))

    def short_name(self, language: str | None = None) -> str:
        language = self._language(language)
        return self.short_translations.get(language, self.short_translations.get("en", ""))

    def display_name(self, language: str | None = None) -> str:
        return self.short_name(language) or self.name(language)

    def __str__(self) -> str:
        return self.name()

    def get_absolute_url(self) -> str:
        return reverse("search") + "?" + urlencode({"tags": self.slug})
