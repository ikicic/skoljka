from django.conf import settings
from django.db import models

from skoljka.apps.problems.models import Problem


class Submission(models.Model):
    id: int
    user_id: int
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions"
    )
    problem_id: int
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="submissions"
    )
    answer = models.JSONField(null=True, blank=True)
    solved = models.BooleanField(default=False)
    solved_at = models.DateTimeField(null=True, blank=True)
    note_md = models.TextField(blank=True)
    note_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "problem"], name="unique_submission"),
        ]

    def __str__(self) -> str:
        return f"Submission({self.user}, {self.problem})"


class Bookmark(models.Model):
    id: int
    user_id: int
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks"
    )
    problem_id: int
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="bookmarks"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "problem"], name="unique_bookmark"),
        ]

    def __str__(self) -> str:
        return f"Bookmark({self.user}, {self.problem})"


class Like(models.Model):
    id: int
    user_id: int
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes"
    )
    problem_id: int
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "problem"], name="unique_like"),
        ]

    def __str__(self) -> str:
        return f"Like({self.user}, {self.problem})"


class FavoriteSource(models.Model):
    id: int
    user_id: int
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_sources"
    )
    source_id: int
    source = models.ForeignKey(
        "sources.Source", on_delete=models.CASCADE, related_name="favorited_by"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "source"], name="unique_favorite_source"),
        ]

    def __str__(self) -> str:
        return f"FavoriteSource({self.user}, {self.source})"


class FavoriteProblemList(models.Model):
    id: int
    user_id: int
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_problem_lists"
    )
    problem_list_id: int
    problem_list = models.ForeignKey(
        "lists.ProblemList", on_delete=models.CASCADE, related_name="favorited_by"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "problem_list"], name="unique_favorite_problem_list"),
        ]

    def __str__(self) -> str:
        return f"FavoriteProblemList({self.user}, {self.problem_list})"
