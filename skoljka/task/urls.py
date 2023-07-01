from django.conf.urls.defaults import include, patterns, url
from django.views.generic import TemplateView

import skoljka.task.views as views
from skoljka.task.models import Task

urlpatterns = patterns(
    '',
    # TODO: this ajax url is different from the other ajax urls
    (r'^ajax/bulk/preview/', 'skoljka.task.ajax.bulk_preview'),
    (r'^ajax/prerequisites/', 'skoljka.task.ajax.prerequisites'),
    (r'^$', views.task_list),
    (r'^user/(?P<user_id>\d+)/$', views.task_list),
    (r'^(?P<id>\d+)/$', views.detail),
    (r'^(?P<task_id>\d+)/similar/$', views.similar),
    (r'^new/$', views.new),
    (r'^new/bulk/$', views.bulk_new),
    (r'^new/bulk/success/$', views.bulk_new_success),
    (r'^new/file/$', views.new_file),
    (r'^new/json/$', views.json_new),
    (r'^new/lecture/$', views.new_lecture),
    (r'^(?P<task_id>\d+)/edit/$', views.new),
    # this url format used to keep robots away with Disallow: /task/export/
    (r'^export/$', views.export),
    (r'^export/(?P<format>\w+)/(?P<ids>[0-9,]+)/', views.export),
    (r'^new/finish/$', TemplateView.as_view(template_name='task_new_finish.html')),
)
