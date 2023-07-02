from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    '',
    (r'^edit/(?P<type_id>\d+)/(?P<id>\d+)/$', 'skoljka.permissions.views.edit'),
)
