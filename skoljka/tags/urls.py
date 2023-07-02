from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    '',
    (r'^tags/$', 'skoljka.tags.views.list'),
)
