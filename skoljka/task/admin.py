from django.contrib import admin

from skoljka.mathcontent.utils import \
        create_file_thumbnail, ThumbnailRenderingException
from skoljka.utils.string_operations import media_path_to_url

from skoljka.task.models import Task, TaskBulkTemplate

class TaskAdmin(admin.ModelAdmin):
    actions = ['refresh_thumbnails']

    def refresh_thumbnails(self, request, queryset):
        generated = 0
        errors = 0
        for task in queryset:
            if task.is_file():
                filename = task.file_attachment.get_full_path_and_filename()
                try:
                    thumbnail_filename = create_file_thumbnail(filename)
                except ThumbnailRenderingException:
                    errors += 1
                    continue
                generated += 1
                task.cache_file_attachment_thumbnail_url = \
                        media_path_to_url(thumbnail_filename)
                task.save()

        self.message_user(request,
                "Generated {} thumbnail(s). {} error(s).".format(
                    generated, errors))


admin.site.register(Task, TaskAdmin)
admin.site.register(TaskBulkTemplate, admin.ModelAdmin)
