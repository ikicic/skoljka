from django.contrib import admin

from skoljka.apps.lists.models import ProblemList, ProblemListItem


class ProblemListItemInline(admin.TabularInline):
    model = ProblemListItem
    extra = 0
    raw_id_fields = ("problem",)


@admin.register(ProblemList)
class ProblemListAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "is_public", "created_at", "updated_at")
    list_filter = ("is_public",)
    search_fields = ("title",)
    raw_id_fields = ("created_by",)
    inlines = [ProblemListItemInline]
