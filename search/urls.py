from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView

urlpatterns = patterns('',
    (r'^([a-zA-Z0-9 ]+)/$', 'search.views.search'),
    (r'^$', 'search.views.search'),
)