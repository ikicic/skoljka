from django.contrib import admin
from permissions.models import PerObjectGroupPermission, PerObjectUserPermission

admin.site.register(PerObjectUserPermission)
admin.site.register(PerObjectGroupPermission)
