from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse

from skoljka.apps.sources.models import Source
from skoljka.apps.tags.models import Tag
from skoljka.utils.permissions import PermissionModel


class Problem(PermissionModel):
    source_id: int | None
    source = models.ForeignKey(
        Source, on_delete=models.SET_NULL, null=True, blank=True, related_name="problems"
    )
    year = models.IntegerField(null=True, blank=True)
    problem_label = models.CharField(max_length=32, blank=True)
    title = models.CharField(max_length=255, blank=True)
    expected_answer = models.JSONField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    content = GenericRelation(
        "content.Content",
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        ordering = ["source", "year", "problem_label"]
        indexes = [
            models.Index(fields=["source", "year"], name="problem_source_year_idx"),
            models.Index(fields=["source", "year", "problem_label"], name="problem_source_year_label_idx"),
        ]

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        if self.source and self.year and self.problem_label:
            return f"{self.source.name()} {self.year} Problem {self.problem_label}"
        if self.source and self.year:
            return f"{self.source.name()} {self.year}"
        return "(unnamed problem)"

    def get_content(self, language: str = "en"):
        """Get the Content object for this problem."""
        from skoljka.apps.content.models import Content

        return self.content.first()

    def __str__(self) -> str:
        return self.display_title

    def get_absolute_url(self) -> str:
        return reverse("problem_detail", kwargs={"pk": self.pk})
