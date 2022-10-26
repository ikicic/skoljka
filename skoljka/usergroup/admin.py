from django.contrib import admin

from skoljka.usergroup.models import UserGroup

class UserGroupAdmin(admin.ModelAdmin):
    actions = ['refresh_member_count']

    def refresh_member_count(self, request, queryset):
        """
        Refresh group member count for selected groups.
        """
        for group_data in queryset:
            group_data.cache_member_count = group_data.get_members().count()
            group_data.save()

admin.site.register(UserGroup, UserGroupAdmin)

