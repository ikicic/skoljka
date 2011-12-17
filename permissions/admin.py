from django.contrib import admin
from permissions.models import PerObjectGroupPermission
#from permissions.models import PerObjectUserPermission

#admin.site.register(PerObjectUserPermission)
admin.site.register(PerObjectGroupPermission)
