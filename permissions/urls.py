from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView

urlpatterns = patterns('',
    (r'^edit/(?P<type_id>\d+)/(?P<id>\d+)/$', 'permissions.views.edit'),
)
