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

    (r'^', include('base.urls')),

    (r'^folder/', include('folder.urls')),
    (r'^usergroup/', include('usergroup.urls')),
    (r'^search/', include('search.urls')),
    (r'^task/', include('task.urls')),
    (r'^', include('post.urls')), # namjerno nije r'^post/'
    (r'^', include('userprofile.urls')), # namjerno nije r'^profile/'
    (r'^', include('solution.urls')), # namjerno nije r'^solution/'

    (r'^sentry/', include('sentry.web.urls')),

)
