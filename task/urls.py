from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView
from task.models import Task

urlpatterns = patterns('',
    (r'^$', 'task.views.task_list'),

    (r'^(?P<id>\d+)/$', 'task.views.detail'),
    (r'^multiple/(?P<ids>[0-9,]+)/$', 'task.views.detail_multiple'),

    (r'^new/$', 'task.views.new'),
    (r'^new/advanced/$', 'task.views.advanced_new'),
    (r'^(?P<task_id>\d+)/edit/$', 'task.views.new'),
    
    # this url format to keep robots away with Disallow: /task/export/
    (r'^export/latex/(?P<ids>[0-9,]+)/', 'task.views.export_to_latex'),
    (r'^export/pdf/(?P<ids>[0-9,]+)/', 'task.views.export_to_pdf'),
    (r'^new/finish/$',
        TemplateView.as_view(template_name='task_new_finish.html')),
)
