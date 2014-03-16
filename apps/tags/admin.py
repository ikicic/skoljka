from django.contrib import admin
from tags.models import Tag, TaggedItem

admin.site.register(Tag)
admin.site.register(TaggedItem)