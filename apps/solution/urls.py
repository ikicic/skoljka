from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView

from solution.models import Solution

urlpatterns = patterns('',
    (r'^ajax/task/(?P<task_id>\d+)/$', 'solution.views.task_ajax'),
    (r'^task/(?P<task_id>\d+)/submit/$', 'solution.views.submit'),
    (r'^task/(?P<task_id>\d+)/mark/$', 'solution.views.mark'),
    (r'^solution/$', 'solution.views.solution_list' ),
    (r'^solution/(?P<solution_id>\d+)/$', 'solution.views.detail'),
    (r'^solution/(?P<solution_id>\d+)/edit/$', 'solution.views.submit'),
    (r'^solution/(?P<solution_id>\d+)/edit/mark/$', 'solution.views.edit_mark'),
    (r'^solution/task/(?P<task_id>\d+)/$', 'solution.views.solution_list'),
    (r'^solution/user/(?P<user_id>\d+)/$', 'solution.views.solution_list'),
    (r'^solution/user/(?P<user_id>\d+)/(?P<status>[_a-z,]+)/$', 'solution.views.solution_list'),
    (r'^solution/task/(?P<task_id>\d+)/user/(?P<user_id>\d+)/$', 'solution.views.solution_list'),
)
