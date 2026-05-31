from django.db import models
from django.urls import reverse

from skoljka.apps.problems.models import Problem
from skoljka.utils.permissions import PermissionModel


class ProblemList(PermissionModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("list_detail", kwargs={"pk": self.pk})


class ProblemListItem(models.Model):
    id: int
    problem_list_id: int
    problem_list = models.ForeignKey(
        ProblemList, on_delete=models.CASCADE, related_name="items"
    )
    problem_id: int
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="list_items"
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["problem_list", "problem"], name="unique_list_item"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.problem_list.title}: {self.problem}"
