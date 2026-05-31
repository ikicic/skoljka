from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from skoljka.apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    search_fields = ("username", "email")
    fieldsets = (*(BaseUserAdmin.fieldsets or ()), (
        "Školjka", {"fields": ("profile_public", "personal_group")},
    ))
