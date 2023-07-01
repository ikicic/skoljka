from django.conf.urls.defaults import include, patterns, url

urlpatterns = patterns(
    '',
    (r'^tags/$', 'skoljka.tags.views.list'),
)
