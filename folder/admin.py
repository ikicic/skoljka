from django.contrib import admin

from folder.models import Folder
from folder.utils import refresh_cache as _refresh_cache

class FolderAdmin(admin.ModelAdmin):
    actions = ['refresh_cache']

    def refresh_cache(self, request, queryset):
        _refresh_cache(queryset)


admin.site.register(Folder, FolderAdmin)
