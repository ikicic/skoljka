from django.contrib import admin

from skoljka.apps.sources.models import Source, SourceDocument


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("slug", "parent", "order", "is_public", "created_by")
    list_filter = ("is_public",)
    search_fields = ("slug", "translations")
    raw_id_fields = ("parent", "created_by")
    filter_horizontal = ("tags",)


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ("label", "source", "year", "language", "kind", "uploaded_by", "created_at")
    list_filter = ("kind", "language", "year")
    search_fields = ("title", "original_filename", "source__slug", "source__translations")
    raw_id_fields = ("source", "uploaded_by")
    readonly_fields = ("created_at",)
