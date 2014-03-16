from django.contrib import admin

from tags.utils import replace_with_original_tags

from folder.models import Folder
from folder.utils import refresh_path_cache as _refresh_path_cache

class FolderAdmin(admin.ModelAdmin):
    actions = ['refresh_path_cache', 'refresh_cache_tags', 'migrate061_070']

    def refresh_path_cache(self, request, queryset):
        _refresh_path_cache(queryset)

    def refresh_cache_tags(self, request, queryset):
        for folder in queryset:
            folder._refresh_cache_tags()

    def migrate061_070(self, request, queryset):
        for folder in queryset:
            tags = folder.cache_tags
            folder.tags.set(*replace_with_original_tags(tags))
            folder._refresh_cache_tags()
    migrate061_070.short_description = "Migrate v0.6.1 to v0.7"


admin.site.register(Folder, FolderAdmin)
