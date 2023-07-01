from django.conf.urls.defaults import include, patterns, url
from django.views.generic import DetailView, ListView, TemplateView

import skoljka.solution.views as views
from skoljka.solution.models import Solution

urlpatterns = patterns(
    '',
    (r'^ajax/task/(?P<task_id>\d+)/$', views.task_ajax),
    (r'^task/(?P<task_id>\d+)/submit/$', views.submit),
    (r'^task/(?P<task_id>\d+)/mark/$', views.mark),
    (r'^solution/$', views.solution_list),
    (r'^solution/(?P<solution_id>\d+)/$', views.detail),
    (r'^solution/(?P<solution_id>\d+)/edit/$', views.submit),
    (r'^solution/(?P<solution_id>\d+)/edit/mark/$', views.edit_mark),
    (r'^solution/task/(?P<task_id>\d+)/$', views.solution_list),
    (r'^solution/user/(?P<user_id>\d+)/$', views.solution_list),
    (r'^solution/user/(?P<user_id>\d+)/(?P<status>[_a-z,]+)/$', views.solution_list),
    (r'^solution/task/(?P<task_id>\d+)/user/(?P<user_id>\d+)/$', views.solution_list),
)
