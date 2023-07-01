from django.conf.urls.defaults import include, patterns, url
from django.views.generic import DetailView, ListView, TemplateView

urlpatterns = patterns(
    '',
    (r'^$', 'skoljka.search.views.view'),
)
