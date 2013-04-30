from django.contrib import admin

from mathcontent.models import Attachment

class AttachmentAdmin(admin.ModelAdmin):
    actions = ['refresh_file_size']

    def refresh_file_size(self, request, queryset):
        for attachment in queryset:
            try:
                attachment.cache_file_size = attachment.file.size
            except:
                attachment.cache_file_size = -1
            attachment.save()

admin.site.register(Attachment, AttachmentAdmin)
