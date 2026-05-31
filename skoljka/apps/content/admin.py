from django.contrib import admin, messages

from skoljka.apps.content.models import Content, ContentAttachment, ContentVersion


class ContentVersionInline(admin.TabularInline):
    model = ContentVersion
    extra = 0
    readonly_fields = ("edited_by", "edited_at", "edit_summary")
    fields = ("edited_at", "edited_by", "edit_summary")


class ContentAttachmentInline(admin.TabularInline):
    model = ContentAttachment
    extra = 0
    fields = ("name", "file", "mime_type", "size", "width", "height")


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ("id", "content_type", "object_id", "original_language")
    list_filter = ("content_type", "original_language")
    search_fields = ("search_text",)
    raw_id_fields = ("content_type",)
    inlines = [ContentAttachmentInline, ContentVersionInline]
    actions = ["rebuild_compiled_html"]

    @admin.action(description="Rebuild compiled HTML")
    def rebuild_compiled_html(self, request, queryset):
        rebuilt = 0
        failed = 0
        for content in queryset:
            try:
                content.save()
            except Exception as exc:
                failed += 1
                self.message_user(
                    request,
                    f"Failed to rebuild content {content.pk}: {exc}",
                    messages.ERROR,
                )
            else:
                rebuilt += 1
        if rebuilt:
            self.message_user(
                request,
                f"Rebuilt compiled HTML for {rebuilt} content item(s).",
                messages.SUCCESS,
            )
        if failed and not rebuilt:
            self.message_user(
                request,
                f"Failed to rebuild {failed} content item(s).",
                messages.ERROR,
            )


@admin.register(ContentVersion)
class ContentVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "content", "edited_by", "edited_at", "edit_summary")
    list_filter = ("edited_at",)
    raw_id_fields = ("content", "edited_by")


@admin.register(ContentAttachment)
class ContentAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "content", "name", "mime_type", "size", "created_at")
    search_fields = ("name",)
    raw_id_fields = ("content",)
