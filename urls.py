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

    # Delegate unqualified URL requests to app home
    # Watch out: base urls can only handle empty strings
    (r'^$', include('base.urls')),

    (r'^task/', include('task.urls')),
    (r'^', include('solution.urls')), # namjerno nije r'^solution/'

    (r'^sentry/', include('sentry.web.urls')),

    # Using existing views
    (r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}),
    (r'^register/$', 'base.views.register'),
)
