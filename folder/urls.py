from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView
from task.models import Task

urlpatterns = patterns('',
    (r'^$', 'folder.views.view'),
    (r'^(?P<path>[-a-zA-Z0-9/ ]+)/$', 'folder.views.view'),
)
