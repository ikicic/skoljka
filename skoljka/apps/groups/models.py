from django.conf import settings
from django.db import models


class Group(models.Model):
    id: int
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    personal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class GroupMembership(models.Model):
    class Role(models.TextChoices):
        MEMBER = "member"
        EDITOR = "editor"
        ADMIN = "admin"

    id: int
    group_id: int
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="memberships"
    )
    user_id: int
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["group", "user"], name="unique_group_membership"),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.group} ({self.role})"
