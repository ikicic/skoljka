from django.contrib import admin

from solution.models import Solution

class SolutionAdmin(admin.ModelAdmin):
    actions = ['refresh_detailed_status']

    def refresh_detailed_status(self, request, queryset):
        for x in queryset:
            # call pre_save
            x.save()

admin.site.register(Solution, SolutionAdmin)
