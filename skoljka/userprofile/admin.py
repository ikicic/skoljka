from django.contrib import admin

from skoljka.userprofile.models import UserProfile, user_refresh_group_cache


class UserProfileAdmin(admin.ModelAdmin):
    actions = ['refresh_task_distribution', 'refresh_group_cache']

    def refresh_task_distribution(self, request, queryset):
        """
        Refresh task difficulty distribution for given users.
        Please note that this isn't really fast. Call only if necessary.
        """
        for user in queryset:
            user.refresh_diff_distribution()

    def refresh_group_cache(self, request, queryset):
        user_ids = list(queryset.values_list('user_id', flat=True))
        user_refresh_group_cache(user_ids)


admin.site.register(UserProfile, UserProfileAdmin)
