from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    
    (r'^sentry/', include('sentry.web.urls')),

    # For serving static files
    (r'static/(?P<path>.*)$', 'django.views.static.serve'),

    # Delegate unqualified URL requests to app home
    (r'^$', include('base.urls')),

    (r'^task/', include('task.urls')),

    # Using existing views
    (r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}),
)
