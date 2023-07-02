from django.contrib import admin

from skoljka.folder.models import Folder
from skoljka.folder.utils import refresh_path_cache as _refresh_path_cache


class FolderAdmin(admin.ModelAdmin):
    actions = ['refresh_path_cache', 'refresh_cache_tags', 'migrate061_070']

    def refresh_path_cache(self, request, queryset):
        _refresh_path_cache(queryset)

    def refresh_cache_tags(self, request, queryset):
        for folder in queryset:
            folder.refresh_cache_tags()

    # Not supported anymore.
    # def migrate061_070(self, request, queryset):
    #     pass


admin.site.register(Folder, FolderAdmin)
