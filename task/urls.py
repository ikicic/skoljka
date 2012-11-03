from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView
from task.models import Task

urlpatterns = patterns('',
    (r'^$', 'task.views.task_list'),
    (r'^user/(?P<user_id>\d+)/$', 'task.views.task_list'),

    (r'^(?P<id>\d+)/$', 'task.views.detail'),
    (r'^(?P<id>\d+)/similar/$', 'task.views.similar'),
    
    (r'^new/$', 'task.views.new'),
    (r'^new/advanced/$', 'task.views.advanced_new'),
    (r'^(?P<task_id>\d+)/edit/$', 'task.views.new'),
    
    # this url format used to keep robots away with Disallow: /task/export/
    (r'^export/(?P<format>\w+)/(?P<ids>[0-9,]+)/', 'task.views.export'),
    (r'^new/finish/$',
        TemplateView.as_view(template_name='task_new_finish.html')),
)
