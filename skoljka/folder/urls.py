from django.conf.urls.defaults import patterns

import skoljka.folder.views as views

urlpatterns = patterns('',
    (r'^select/(?P<id>\d+)/$', views.select),
    (r'^select/task/(?P<task_id>\d+)/$', views.select_task),

    (r'^new/$', views.new),
    (r'^new/advanced/$', views.advanced_new),
    (r'^(?P<folder_id>\d+)/delete/$', views.delete),
    (r'^(?P<folder_id>\d+)/edit/$', views.new),
    (r'^(?P<folder_id>\d+)/edit/tasks/$', views.edit_tasks),

    (r'^$', views.view),
    (r'^my/$', views.folder_my),
    (r'^(?P<folder_id>\d+)/(?P<path>[-a-zA-Z0-9/]*)$', views.view),

    (r'^(?P<path>[-a-zA-Z0-9/]*)$', views.redirect_by_path),
)
