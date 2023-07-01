from django.conf.urls.defaults import include, patterns, url
from django.views.generic import DetailView, ListView, TemplateView

urlpatterns = patterns(
    '',
    (r'^edit/(?P<type_id>\d+)/(?P<id>\d+)/$', 'skoljka.permissions.views.edit'),
)
