from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    '',
    (r'^$', 'skoljka.search.views.view'),
)
