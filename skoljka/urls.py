from django.conf import settings
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    # For serving static files
    (r'static/(?P<path>.*)$', 'django.views.static.serve'),
    (
        r'media/(?P<path>.*)$',
        'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT},
    ),
    (r'^', include('skoljka.base.urls')),
    (r'^', include('skoljka.competition.urls')),
    (r'^folder/', include('skoljka.folder.urls')),
    (r'^lectures/$', 'skoljka.task.views.lectures_list'),
    (r'^lectures/list/$', 'skoljka.task.views.lectures_as_list'),
    (r'^', include('skoljka.mathcontent.urls')),  # namjerno nije r'^mathcontent/'
    (r'^permissions/', include('skoljka.permissions.urls')),
    (r'^pm/', include('skoljka.pm.urls')),
    (r'^', include('skoljka.rating.urls')),
    (r'^search/', include('skoljka.search.urls')),
    (r'^', include('skoljka.tags.urls')),
    (r'^task/', include('skoljka.task.urls')),
    (r'^usergroup/', include('skoljka.usergroup.urls')),
    (r'^', include('skoljka.post.urls')),  # namjerno nije r'^post/'
    (r'^', include('skoljka.userprofile.urls')),  # namjerno nije r'^profile/'
    (r'^', include('skoljka.solution.urls')),  # namjerno nije r'^solution/'
    # (r'^sentry/', include('sentry.web.urls')),
)
