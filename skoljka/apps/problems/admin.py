from django.contrib import admin

from skoljka.apps.problems.models import Problem


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "source", "year", "problem_label", "is_public", "created_by")
    list_filter = ("is_public", "source", "year")
    search_fields = ("title",)
    raw_id_fields = ("source", "created_by")
    filter_horizontal = ("tags",)
