from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView
from task.models import Task

urlpatterns = patterns('',
    # TODO: this ajax url is different from the other ajax urls
    (r'^ajax/bulk/preview/', 'task.ajax.bulk_preview'),
    (r'^ajax/prerequisites/', 'task.ajax.prerequisites'),
    (r'^$', 'task.views.task_list'),
    (r'^user/(?P<user_id>\d+)/$', 'task.views.task_list'),

    (r'^(?P<id>\d+)/$', 'task.views.detail'),
    (r'^(?P<task_id>\d+)/similar/$', 'task.views.similar'),

    (r'^new/$', 'task.views.new'),
    (r'^new/bulk/$', 'task.views.bulk_new'),
    (r'^new/bulk/success/$', 'task.views.bulk_new_success'),
    (r'^new/file/$', 'task.views.new_file'),
    (r'^new/json/$', 'task.views.json_new'),
    (r'^new/lecture/$', 'task.views.new_lecture'),
    (r'^(?P<task_id>\d+)/edit/$', 'task.views.new'),

    # this url format used to keep robots away with Disallow: /task/export/
    (r'^export/$', 'task.views.export'),
    (r'^export/(?P<format>\w+)/(?P<ids>[0-9,]+)/', 'task.views.export'),
    (r'^new/finish/$',
        TemplateView.as_view(template_name='task_new_finish.html')),
)
