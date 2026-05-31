from django.contrib import admin

from skoljka.apps.groups.models import Group, GroupMembership


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 0
    raw_id_fields = ("user",)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "personal", "created_at")
    list_filter = ("personal",)
    search_fields = ("name", "slug")
    inlines = [GroupMembershipInline]
