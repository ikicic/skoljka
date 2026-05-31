from skoljka.apps.accounts.models import User

from typing import Literal

from django.conf import settings
from django.db import models
from django.db.models import Q

PermissionType = Literal["view", "edit"]


class PermissionQuerySet(models.QuerySet):
    """QuerySet with permission-aware filtering.

    Usage:
        Problem.objects.for_user(user)                # viewable
        Problem.objects.for_user(user, "edit")         # editable
        Problem.objects.for_user(user).filter(year=2024)  # composable
    """

    def for_user(self, user, permission: PermissionType = "view") -> "PermissionQuerySet":
        if not user.is_authenticated:
            return self.filter(is_public=True)
        if user.is_staff:
            return self
        if permission == "view":
            return self.filter(Q(is_public=True) | Q(created_by=user))
        # edit, admin
        return self.filter(created_by=user)


class PermissionModel(models.Model):
    """Abstract base for models with owner-based permissions."""

    id: int
    is_public = models.BooleanField(default=True)
    created_by_id: int | None
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )

    objects = PermissionQuerySet.as_manager()

    class Meta:
        abstract = True

    def user_has_perm(self, user: User, permission: PermissionType = "view") -> bool:
        if user.is_staff:
            return True
        if permission == "view" and self.is_public:
            return True
        if not user.is_authenticated:
            return False
        return self.created_by_id == user.pk
