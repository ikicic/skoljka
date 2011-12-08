from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView
from task.models import Task

urlpatterns = patterns('',
    (r'^$', 'task.views.list'),

    (r'^(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Task,
            template_name='task_detail.html')),

    (r'^new/$', 'task.views.new'),
    (r'^(?P<task_id>\d+)/edit/$', 'task.views.new'),
    (r'^new/finish/$',
        TemplateView.as_view(template_name='task_new_finish.html')),
)
