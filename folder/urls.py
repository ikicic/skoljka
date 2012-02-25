from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView
from task.models import Task

urlpatterns = patterns('',
    (r'^$', 'folder.views.view'),
    (r'^(?P<id>\d+)/', 'folder.views.detail_by_id'),
    (r'^select/(?P<id>\d+)/', 'folder.views.select'),
    (r'^select/task/(?P<task_id>\d+)/', 'folder.views.select_task'),
    (r'^(?P<path>[-a-zA-Z0-9/ ]+)/$', 'folder.views.view'),
)
