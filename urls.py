from django.conf import settings
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # For serving static files
    (r'static/(?P<path>.*)$', 'django.views.static.serve'),
    (r'media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),

    (r'^', include('base.urls')),

    (r'^activity/', include('activity.urls')),
    (r'^folder/', include('folder.urls')),
    (r'^', include('mathcontent.urls')), # namjerno nije r'^mathcontent/'
    (r'^permissions/', include('permissions.urls')),
    (r'^pm/', include('pm.urls')),
    (r'^', include('rating.urls')),
    (r'^search/', include('search.urls')),
    (r'^', include('tags.urls')),
    (r'^task/', include('task.urls')),
    (r'^usergroup/', include('usergroup.urls')),
    (r'^', include('post.urls')), # namjerno nije r'^post/'
    (r'^', include('userprofile.urls')), # namjerno nije r'^profile/'
    (r'^', include('solution.urls')), # namjerno nije r'^solution/'

    # (r'^sentry/', include('sentry.web.urls')),
)
