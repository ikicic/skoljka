from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id: int
    email = models.EmailField(unique=True)
    profile_public = models.BooleanField(default=True)
    personal_group_id: int | None
    personal_group = models.ForeignKey(
        "groups.Group", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="personal_group_user",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.username

    def ensure_personal_group(self) -> "models.ForeignKey":
        """Create personal group if it doesn't exist, return it."""
        if self.personal_group_id:
            return self.personal_group
        from skoljka.apps.groups.models import Group, GroupMembership
        group = Group.objects.create(
            name=self.username,
            slug=f"user-{self.pk}",
            personal=True,
        )
        GroupMembership.objects.create(
            group=group, user=self, role=GroupMembership.Role.ADMIN,
        )
        self.personal_group = group
        self.save(update_fields=["personal_group"])
        return group
