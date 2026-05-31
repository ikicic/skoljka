from django.contrib import admin

from skoljka.apps.news.models import NewsPost


@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "hidden", "created_by")
    list_filter = ("hidden",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("created_by",)
