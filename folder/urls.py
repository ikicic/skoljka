from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^select/(?P<id>\d+)/$', 'folder.views.select'),
    (r'^select/task/(?P<task_id>\d+)/$', 'folder.views.select_task'),

    (r'^new/$', 'folder.views.new'),
    (r'^new/advanced/$', 'folder.views.advanced_new'),
    (r'^(?P<folder_id>\d+)/delete/$', 'folder.views.delete'),
    (r'^(?P<folder_id>\d+)/edit/$', 'folder.views.new'),
    (r'^(?P<folder_id>\d+)/edit/tasks/$', 'folder.views.edit_tasks'),

    (r'^$', 'folder.views.view'),
    (r'^my/$', 'folder.views.folder_my'),
    (r'^(?P<folder_id>\d+)/(?P<path>[-a-zA-Z0-9/]*)$', 'folder.views.view'),

    (r'^(?P<path>[-a-zA-Z0-9/]*)$', 'folder.views.redirect_by_path'),
)
