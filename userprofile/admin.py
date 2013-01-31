from django.contrib import admin
from userprofile.models import UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    actions = ['refresh_task_distribution']

    def refresh_task_distribution(self, request, queryset):
        """
            Refresh task difficulty distribution for given users.
            Please note that this isn't really fast. Call only if necessary.
        """
        for user in queryset:
            user.refresh_diff_distribution()

admin.site.register(UserProfile, UserProfileAdmin)
