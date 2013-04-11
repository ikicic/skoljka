from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView
from task.models import Task

urlpatterns = patterns('',
    (r'^$', 'folder.views.view'),
    (r'^(?P<id>\d+)/(?P<description>[-a-zA-Z0-9]*)$', 'folder.views.view'),

    (r'^select/(?P<id>\d+)/$', 'folder.views.select'),
    (r'^select/task/(?P<task_id>\d+)/$', 'folder.views.select_task'),

    (r'^new/$', 'folder.views.new'),
    (r'^new/advanced/$', 'folder.views.advanced_new'),
    (r'^(?P<folder_id>\d+)/edit/$', 'folder.views.new'),
    (r'^(?P<folder_id>\d+)/edit/tasks/$', 'folder.views.edit_tasks'),
)
