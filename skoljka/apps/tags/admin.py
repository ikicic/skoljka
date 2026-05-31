from django.contrib import admin

from skoljka.apps.tags.models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("slug", "kind", "parent", "hidden")
    list_filter = ("kind", "hidden")
    search_fields = ("slug", "translations", "short_translations", "descriptions")
    raw_id_fields = ("parent",)
